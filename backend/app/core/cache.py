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
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger("app.cache")

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


async def close() -> None:
    if _client is not None:
        await _client.aclose()
