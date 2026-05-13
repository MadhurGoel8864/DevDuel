"""Rate limiting via Redis fixed-window counters.

Design notes:
- Keys: rl:{scope}:{window}:{limit}:{key}
  The scope component prevents counter sharing between endpoints that coincidentally
  share the same (limit, window) configuration.
- Atomicity: INCR + EXPIRE runs as a single Lua script so a process crash between
  the two operations cannot leave a key without a TTL (permanent lockout).
- Fail-open: if Redis is unavailable, the request is allowed through. Rate limiting
  degrading gracefully is better than taking down login/register with it.

Usage:
    dependencies=[Depends(rate_limit("auth:login", 5, 60))]
    dependencies=[Depends(rate_limit("submit:burst", 1, 8, by="user"))]
"""

import jwt as pyjwt
from fastapi import Depends, Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.exceptions.rate_limit import RateLimitExceededException
from app.core.redis import get_redis_client

_RL_KEY = "rl:{scope}:{window}:{limit}:{key}"

# Atomic increment + conditional TTL set.
# Running as Lua guarantees both operations succeed or neither does from Redis's
# perspective, preventing immortal keys if the Python process crashes mid-flight.
_INCR_EXPIRE_LUA = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


def _client_ip(request: Request) -> str:
    """Real client IP, available after ProxyHeadersMiddleware rewrites request.client."""
    if request.client and request.client.host:
        return request.client.host
    # Defensive fallback — should not occur in production with ProxyHeadersMiddleware.
    # Use a per-request unique key so no two distinct clients share a lockout counter.
    return f"noop-{id(request)}"


def _user_key(request: Request) -> str:
    """JWT sub as rate-limit key; falls back to client IP if token is absent or invalid."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = pyjwt.decode(
                auth[7:],
                settings.effective_jwt_secret,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": False},
            )
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except Exception:
            pass
    return f"ip:{_client_ip(request)}"


async def _enforce(
    redis: Redis, scope: str, key: str, limit: int, window_sec: int
) -> None:
    """Atomically increment fixed-window counter; raise HTTP 429 when limit is exceeded."""
    full_key = _RL_KEY.format(scope=scope, window=window_sec, limit=limit, key=key)
    count = await redis.eval(_INCR_EXPIRE_LUA, 1, full_key, window_sec)

    if count > limit:
        ttl = await redis.ttl(full_key)
        if ttl > 0:
            retry_after = ttl
        elif ttl == 0:
            # Key expires in <1 s — round up to avoid telling client "wait 0 seconds".
            retry_after = 1
        else:
            # ttl == -1 (no expiry, shouldn't happen) or -2 (key gone, race).
            retry_after = window_sec
        raise RateLimitExceededException(retry_after=retry_after)


def rate_limit(scope: str, limit: int, window_sec: int, by: str = "ip"):
    """Return a FastAPI dependency that enforces a fixed-window rate limit.

    scope      — unique endpoint identifier, e.g. "auth:login", "submit:burst".
                 Required to prevent counter collision between endpoints that share
                 the same (limit, window_sec) values.
    limit      — maximum requests allowed per window.
    window_sec — window duration in seconds.
    by="ip"    — key on client IP; use for public/unauthenticated endpoints.
    by="user"  — key on JWT sub (fallback to IP); use for authenticated endpoints.
    """
    async def _dep(
        request: Request,
        redis: Redis = Depends(get_redis_client),
    ) -> None:
        key = _user_key(request) if by == "user" else f"ip:{_client_ip(request)}"
        try:
            await _enforce(redis, scope, key, limit, window_sec)
        except RateLimitExceededException:
            raise
        except RedisError:
            # Fail open on Redis outage — don't take down auth when cache is unavailable.
            pass

    return _dep
