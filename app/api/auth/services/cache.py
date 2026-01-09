import logging

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)


async def store_user_otp(user_id: str, otp: str):
    redis = await get_redis()

    key = f"otp:user:{user_id}"
    logger.info(
        f"Storing OTP for user {user_id} in Redis with key {key} with OTP {otp}"
    )
    await redis.set(name=key, value=otp, ex=settings.OTP_EXPIRE_SECONDS)
