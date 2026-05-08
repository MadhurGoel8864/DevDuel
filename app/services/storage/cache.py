# app/services/storage/cache.py
"""Redis cache layer for GCS test-case downloads.

Cache key: test_cases:{sha256(gcs_url)[:16]}
TTL: 1 hour — test cases change rarely; invalidated explicitly on upload.

Avoids the synchronous GCS download on every submission after the first.
"""
import hashlib
import json
import logging
from typing import Any

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

_TTL_SECONDS = 3600  # 1 hour


def _cache_key(gcs_url: str) -> str:
    url_hash = hashlib.sha256(gcs_url.encode()).hexdigest()[:16]
    return f"test_cases:{url_hash}"


async def get_cached_test_cases(gcs_url: str) -> list[dict[str, Any]] | None:
    """Return cached test cases or None on miss."""
    redis = await get_redis()
    raw = await redis.get(_cache_key(gcs_url))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"[gcs-cache] corrupt cache for {gcs_url!r}, ignoring")
        return None


async def set_cached_test_cases(
    gcs_url: str, test_cases: list[dict[str, Any]]
) -> None:
    """Cache test cases in Redis with a 1-hour TTL."""
    redis = await get_redis()
    await redis.set(_cache_key(gcs_url), json.dumps(test_cases), ex=_TTL_SECONDS)
    logger.debug(f"[gcs-cache] cached {len(test_cases)} test cases for {gcs_url!r}")


async def invalidate_test_cases_cache(gcs_url: str) -> None:
    """Delete cached test cases — call after uploading new test cases for a problem."""
    redis = await get_redis()
    await redis.delete(_cache_key(gcs_url))
    logger.info(f"[gcs-cache] invalidated cache for {gcs_url!r}")
