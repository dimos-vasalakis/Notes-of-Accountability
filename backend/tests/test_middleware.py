from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.middleware import RateLimitMiddleware, RequestContextMiddleware


def _build_app(max_requests: int = 2, window_seconds: float = 60.0) -> FastAPI:
    app = FastAPI()

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ping": "pong"}

    app.add_middleware(
        RateLimitMiddleware, max_requests=max_requests, window_seconds=window_seconds
    )
    app.add_middleware(RequestContextMiddleware)
    return app


def test_request_id_header_is_set() -> None:
    client = TestClient(_build_app())

    response = client.get("/ping")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


def test_rate_limit_blocks_after_threshold() -> None:
    client = TestClient(_build_app(max_requests=2, window_seconds=60.0))

    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200

    blocked = client.get("/ping")
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_health_endpoint_is_exempt_from_rate_limit() -> None:
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.add_middleware(RateLimitMiddleware, max_requests=1, window_seconds=60.0)
    client = TestClient(app)

    for _ in range(5):
        assert client.get("/health").status_code == 200
