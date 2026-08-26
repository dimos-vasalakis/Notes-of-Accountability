import logging
import time
import uuid
from collections import deque
from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger("app.request")

RequestId = str


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns each request a request id and logs method, path, status, and duration."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s %s %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window rate limiter, keyed by client IP.

    Single-process only: sufficient for the current single-instance deployment.
    If the backend is ever scaled horizontally, swap the in-memory store for a
    shared one (e.g. Redis) so limits are enforced across instances.
    """

    def __init__(
        self,
        app: object,
        max_requests: int = settings.rate_limit_requests,
        window_seconds: float = settings.rate_limit_window_seconds,
    ) -> None:
        super().__init__(app)
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not settings.rate_limit_enabled or request.url.path == "/health":
            return await call_next(request)

        client_key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start = now - self._window_seconds

        hits = self._hits.setdefault(client_key, deque())
        while hits and hits[0] < window_start:
            hits.popleft()

        if len(hits) >= self._max_requests:
            retry_after = max(0.0, hits[0] + self._window_seconds - now)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests"},
                headers={"Retry-After": str(int(retry_after) + 1)},
            )

        hits.append(now)
        return await call_next(request)
