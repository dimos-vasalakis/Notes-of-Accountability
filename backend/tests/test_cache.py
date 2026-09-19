"""Cache invalidation: every read that's cached must reflect a write made right after it."""

import pytest
from httpx import AsyncClient

from app.core import cache

USER = {"email": "cache-user@example.com", "password": "supersecret1"}


class FakeRedis:
    """Just enough of redis.asyncio.Redis for app.core.cache, with no TTL handling."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def mget(self, keys: list[str]) -> list[str | None]:
        return [self.store.get(key) for key in keys]

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value

    async def incr(self, key: str) -> int:
        self.store[key] = str(int(self.store.get(key, 0)) + 1)
        return int(self.store[key])

    def pipeline(self, transaction: bool = True) -> "FakePipeline":
        return FakePipeline(self)

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self.store.pop(key, None)


class FakePipeline:
    """Queues sets and applies them on execute(), like redis-py's pipeline."""

    def __init__(self, redis: FakeRedis) -> None:
        self._redis = redis
        self._queued: list[tuple[str, str]] = []

    async def __aenter__(self) -> "FakePipeline":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._queued.append((key, value))

    async def execute(self) -> None:
        for key, value in self._queued:
            self._redis.store[key] = value


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    fake = FakeRedis()
    monkeypatch.setattr(cache, "_get_client", lambda: fake)
    return fake


async def test_bump_version_orphans_old_versions(fake_redis: FakeRedis) -> None:
    assert await cache.get_version("notes", "u1") == 0

    await cache.bump_version("notes", "u1")

    assert await cache.get_version("notes", "u1") == 1
    assert await cache.get_versions(("notes", "tasks"), ["u1", "u2"]) == {
        "u1": (1, 0),
        "u2": (0, 0),
    }


async def test_note_reads_are_cached_and_writes_invalidate(
    client: AsyncClient, fake_redis: FakeRedis
) -> None:
    await client.post("/api/auth/signup", json=USER)
    note = (await client.post("/api/notes", json={"title": "v1"})).json()

    assert [n["title"] for n in (await client.get("/api/notes")).json()] == ["v1"]
    assert (await client.get(f"/api/notes/{note['id']}")).json()["title"] == "v1"
    assert any(key.startswith("notes:list:") for key in fake_redis.store)
    assert any(key.startswith("notes:item:") for key in fake_redis.store)

    await client.patch(f"/api/notes/{note['id']}", json={"title": "v2"})
    assert [n["title"] for n in (await client.get("/api/notes")).json()] == ["v2"]
    assert (await client.get(f"/api/notes/{note['id']}")).json()["title"] == "v2"

    await client.post("/api/notes", json={"title": "another"})
    assert len((await client.get("/api/notes")).json()) == 2

    await client.delete(f"/api/notes/{note['id']}")
    assert len((await client.get("/api/notes")).json()) == 1
    assert (await client.get(f"/api/notes/{note['id']}")).status_code == 404


async def test_completing_a_task_invalidates_the_cached_streak(
    client: AsyncClient, fake_redis: FakeRedis
) -> None:
    await client.post("/api/auth/signup", json=USER)
    assert (await client.get("/api/pods/me/streak")).json()["current_streak"] == 0
    assert any(key.startswith("streak:") for key in fake_redis.store)

    task = (await client.post("/api/tasks", json={"title": "Revise"})).json()
    await client.patch(f"/api/tasks/{task['id']}", json={"status": "done"})

    assert (await client.get("/api/pods/me/streak")).json()["current_streak"] == 1


async def test_logging_a_study_session_invalidates_sessions_and_streak(
    client: AsyncClient, fake_redis: FakeRedis
) -> None:
    await client.post("/api/auth/signup", json=USER)
    assert (await client.get("/api/exam-prep/study-sessions")).json() == []
    assert (await client.get("/api/pods/me/streak")).json()["current_streak"] == 0

    response = await client.post("/api/exam-prep/study-sessions", json={"duration_seconds": 1500})
    assert response.status_code == 201

    assert len((await client.get("/api/exam-prep/study-sessions")).json()) == 1
    assert (await client.get("/api/pods/me/streak")).json()["current_streak"] == 1
