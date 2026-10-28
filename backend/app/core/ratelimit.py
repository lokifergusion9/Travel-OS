"""Fixed-window rate limiting as a FastAPI dependency.

Counters live in Redis so limits hold across Gunicorn workers. If Redis is
unreachable we fall back to a per-process in-memory counter rather than
failing open — weaker across workers, but never unlimited.

    @router.post("/login", dependencies=[Depends(rate_limit("login", 10, 60))])
"""
import logging
import time
from collections.abc import Callable

from fastapi import HTTPException, Request, status
from redis import asyncio as aioredis
from redis.exceptions import RedisError

from app.core.config import settings

log = logging.getLogger("travelos.ratelimit")

_redis: aioredis.Redis | None = None
_memory: dict[str, tuple[int, float]] = {}  # key -> (count, window_expires_at)


def _client() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url, socket_connect_timeout=0.5, socket_timeout=0.5
        )
    return _redis


def client_ip(request: Request) -> str:
    if settings.trust_proxy:
        # nginx appends the address it saw, so the LAST hop is trustworthy;
        # earlier entries are client-supplied.
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def _memory_hit(key: str, window: int) -> int:
    now = time.monotonic()
    count, expires = _memory.get(key, (0, now + window))
    if now >= expires:
        count, expires = 0, now + window
    count += 1
    _memory[key] = (count, expires)
    if len(_memory) > 10_000:  # keep the fallback bounded
        for k in [k for k, (_, e) in _memory.items() if e <= now]:
            _memory.pop(k, None)
    return count


async def _hit(key: str, window: int) -> int:
    try:
        r = _client()
        async with r.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, window, nx=True)
            count, _ = await pipe.execute()
        return int(count)
    except (RedisError, OSError) as exc:
        log.warning("rate limit: redis unavailable (%s); using in-memory fallback", exc)
        return _memory_hit(key, window)


def rate_limit(scope: str, limit: int, window_seconds: int) -> Callable:
    """Allow ``limit`` requests per client IP per ``window_seconds`` for ``scope``."""

    async def dependency(request: Request) -> None:
        if not settings.rate_limit_enabled:
            return
        bucket = int(time.time() // window_seconds)
        key = f"rl:{scope}:{client_ip(request)}:{bucket}"
        if await _hit(key, window_seconds) > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests — please slow down and try again shortly.",
                headers={"Retry-After": str(window_seconds)},
            )

    return dependency
