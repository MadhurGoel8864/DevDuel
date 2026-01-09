from redis.asyncio import Redis

from app.core.config import settings

redis_client: Redis | None = None


async def get_redis() -> Redis:
    """
    Get or create Redis client instance.

    Returns:
        Redis: Redis client instance
    """
    global redis_client

    if redis_client is None:
        redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )

    return redis_client


async def get_redis_client() -> Redis:
    """
    FastAPI dependency to provide Redis client.

    Returns:
        Redis: Redis client instance for dependency injection
    """
    return await get_redis()
