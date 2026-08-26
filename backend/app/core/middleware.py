import logging
import time
import uuid
from collections import OrderedDict, deque
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

    Per-process only: in prod the backend runs with multiple uvicorn workers
    (see backend/Dockerfile), each holding its own counters, so the effective
    limit per client is up to max_requests * worker_count. If the backend is
    ever scaled horizontally or needs an exact global limit, swap this for a
    shared store (e.g. Redis).

    The client key is taken from X-Real-IP when present, since the prod nginx
    config (nginx/nginx.prod.conf) always overwrites that header with the real
    connecting IP before proxying to the backend -- it can't be spoofed by a
    client. Without a trusted proxy in front (e.g. local dev), it falls back
    to the direct connection's IP.
    """

    _MAX_TRACKED_CLIENTS = 10_000

    def __init__(
        self,
        app: object,
        max_requests: int = settings.rate_limit_requests,
        window_seconds: float = settings.rate_limit_window_seconds,
    ) -> None:
        super().__init__(app)
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._hits: OrderedDict[str, deque[float]] = OrderedDict()

    @staticmethod
    def _client_key(request: Request) -> str:
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not settings.rate_limit_enabled or request.url.path == "/health":
            return await call_next(request)

        client_key = self._client_key(request)
        now = time.monotonic()
        window_start = now - self._window_seconds

        hits = self._hits.get(client_key)
        if hits is not None:
            while hits and hits[0] < window_start:
                hits.popleft()
            if not hits:
                del self._hits[client_key]
                hits = None

        if hits is not None:
            self._hits.move_to_end(client_key)
            if len(hits) >= self._max_requests:
                retry_after = max(0.0, hits[0] + self._window_seconds - now)
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Too many requests"},
                    headers={"Retry-After": str(int(retry_after) + 1)},
                )
        else:
            hits = deque()
            self._hits[client_key] = hits
            if len(self._hits) > self._MAX_TRACKED_CLIENTS:
                self._hits.popitem(last=False)

        hits.append(now)
        return await call_next(request)
