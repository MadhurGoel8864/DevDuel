# app/core/arq_pool.py
"""ARQ Redis pool — used to enqueue jobs from FastAPI handlers.

Separate from the redis.asyncio.Redis singleton in app/core/redis.py
because ARQ needs arq.connections.ArqRedis (its own pool type).
"""
from arq.connections import ArqRedis, RedisSettings, create_pool
from fastapi import Request

from app.core.config import settings

_arq_pool: ArqRedis | None = None


def get_arq_redis_settings() -> RedisSettings:
    return RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        database=settings.REDIS_DB,
    )


async def get_arq_pool() -> ArqRedis:
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_pool(get_arq_redis_settings())
    return _arq_pool


async def close_arq_pool() -> None:
    global _arq_pool
    if _arq_pool:
        await _arq_pool.aclose()
        _arq_pool = None


async def get_arq_pool_dep() -> ArqRedis:
    """FastAPI dependency — inject the ARQ pool into handlers."""
    return await get_arq_pool()
