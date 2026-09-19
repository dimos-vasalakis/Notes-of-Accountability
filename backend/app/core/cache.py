"""Redis cache-aside helpers, backed by a plain TCP connection (e.g. Upstash's
redis:// / rediss:// endpoint) rather than a REST proxy.

Redis is optional and best-effort: with no REDIS_URL configured, or on any
RedisError, calls here log (or no-op) and return None/False instead of
raising, so a cache outage or missing config degrades to "always hit the
database" rather than taking the API down.
"""

import asyncio
import json
import logging
import uuid
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger("app.cache")

# Invalidation scopes (see "versioned invalidation" below).
TASKS_SCOPE = "tasks"
NOTES_SCOPE = "notes"
STUDY_SCOPE = "study"
EXAM_REF_SCOPE = "exam_ref"

_client: redis.Redis | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


def _get_client() -> redis.Redis | None:
    """Return a client bound to the current running loop, creating one if needed.

    A client created against one asyncio event loop can't be reused from
    another (e.g. pytest-asyncio gives each test its own loop), so this
    recreates the client whenever the running loop changes instead of
    holding one module-level instance for the process lifetime.
    """
    global _client, _client_loop
    if not settings.redis_url:
        return None
    loop = asyncio.get_running_loop()
    if _client is None or _client_loop is not loop:
        _client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        _client_loop = loop
    return _client


async def get_json(key: str) -> Any | None:
    """Return the cached value for `key`, or None on a miss, cache failure, or no cache."""
    client = _get_client()
    if client is None:
        return None
    try:
        raw = await client.get(key)
    except redis.RedisError:
        logger.warning("cache get failed for key=%s", key, exc_info=True)
        return None
    return json.loads(raw) if raw is not None else None


async def set_json(key: str, value: Any, ttl_seconds: int | None = None) -> None:
    """Cache `value` under `key` for ttl_seconds (defaults to settings.cache_ttl_seconds)."""
    client = _get_client()
    if client is None:
        return
    try:
        await client.set(
            key, json.dumps(value), ex=ttl_seconds or settings.cache_ttl_seconds
        )
    except redis.RedisError:
        logger.warning("cache set failed for key=%s", key, exc_info=True)


async def mset_json(items: dict[str, Any], ttl_seconds: int | None = None) -> None:
    """Batch `set_json`: every entry written in one pipelined round trip."""
    client = _get_client()
    if client is None or not items:
        return
    try:
        async with client.pipeline(transaction=False) as pipe:
            for key, value in items.items():
                pipe.set(key, json.dumps(value), ex=ttl_seconds or settings.cache_ttl_seconds)
            await pipe.execute()
    except redis.RedisError:
        logger.warning("cache mset failed for %d keys", len(items), exc_info=True)


async def delete(*keys: str) -> None:
    """Evict one or more cache keys."""
    client = _get_client()
    if client is None or not keys:
        return
    try:
        await client.delete(*keys)
    except redis.RedisError:
        logger.warning("cache delete failed for keys=%s", keys, exc_info=True)


async def incr(key: str) -> int | None:
    """Atomically increment (and create, if missing) an integer counter key."""
    client = _get_client()
    if client is None:
        return None
    try:
        return await client.incr(key)
    except redis.RedisError:
        logger.warning("cache incr failed for key=%s", key, exc_info=True)
        return None


async def mget_json(keys: list[str]) -> list[Any | None]:
    """Batch `get_json`: one round trip, None for each miss (or for every key on failure)."""
    client = _get_client()
    if client is None or not keys:
        return [None] * len(keys)
    try:
        raws = await client.mget(keys)
    except redis.RedisError:
        logger.warning("cache mget failed for %d keys", len(keys), exc_info=True)
        return [None] * len(keys)
    return [json.loads(raw) if raw is not None else None for raw in raws]


# --- versioned invalidation -------------------------------------------------
#
# Each (scope, subject) pair -- e.g. ("notes", <owner uuid>) -- has an integer
# version. Cached entries embed the version in their key, so bumping it orphans
# every entry at once. An atomic INCR (rather than deleting known keys) also
# closes the read/write race: a reader that started before a mutation commits
# but writes after it lands under the old, now-unreachable version and just
# expires via TTL. Callers must read the version *before* querying the DB.


def _version_key(scope: str, subject: uuid.UUID | str) -> str:
    return f"{scope}:version:{subject}"


async def get_versions(
    scopes: tuple[str, ...], subjects: list[uuid.UUID | str]
) -> dict[uuid.UUID | str, tuple[int, ...]]:
    """Current versions of every scope for every subject, in a single round trip."""
    raws = await mget_json(
        [_version_key(scope, subject) for subject in subjects for scope in scopes]
    )
    width = len(scopes)
    return {
        subject: tuple(
            raw if isinstance(raw, int) else 0 for raw in raws[i * width : (i + 1) * width]
        )
        for i, subject in enumerate(subjects)
    }


async def get_version(scope: str, subject: uuid.UUID | str) -> int:
    """Current version of one scope for one subject (0 if never bumped)."""
    return (await get_versions((scope,), [subject]))[subject][0]


async def bump_version(scope: str, subject: uuid.UUID | str) -> None:
    """Invalidate everything cached under (scope, subject)."""
    await incr(_version_key(scope, subject))


async def close() -> None:
    if _client is not None:
        await _client.aclose()
