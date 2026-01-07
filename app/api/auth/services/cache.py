from app.core.redis import get_redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


async def store_user_otp(user_id: int, otp: str):
    redis = await get_redis()
    logging.info(f"Redis connection established: {redis}")
    key = f"otp:user:{user_id}"
    logger.info(
        f"Storing OTP for user {user_id} in Redis with key {key} with OTP {otp}"
    )
    await redis.set(name=key, value=otp, ex=settings.OTP_EXPIRE_SECONDS)
