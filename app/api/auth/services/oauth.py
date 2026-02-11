import logging
import uuid
from urllib.parse import urlencode

import httpx
from fastapi import Depends
from redis.asyncio import Redis

from app.api.users.dao.users import UserDAO, get_user_dao
from app.api.users.services import UserService, get_user_service
from app.core.config import settings
from app.core.exceptions import BadRequestException
from app.core.redis import get_redis_client
from app.database.models.users import User

logger = logging.getLogger(__name__)


class GoogleOAuthService:
    def __init__(self, redis: Redis, user_service: UserService, user_dao: UserDAO):
        self._AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
        self._TOKEN_URL = "https://oauth2.googleapis.com/token"
        self._USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
        self._redis = redis
        self._user_service = user_service
        self._user_dao = user_dao

    async def authenticate_google_user(self, code: str) -> User:
        token_data = await self.exchange_code_for_token(code)
        user_info = await self.fetch_user_profile(token_data["access_token"])

        user = await self._user_service.get_or_create_oauth_user(
            email=user_info["email"],
            provider="google",
            provider_user_id=user_info["sub"],
            full_name=user_info.get("name"),
        )

        # Update last login timestamp
        try:
            await self._user_dao.update_last_login(user.id)
            logger.info(f"Updated last_login_at for OAuth user {user.email}")
        except Exception as e:
            # Log error but don't fail authentication
            logger.error(
                f"Failed to update last_login_at for OAuth user {user.email}: {e}"
            )

        return user

    def get_auth_url(self, state: str) -> str:
        logger.info("Redirecting to Google OAuth login page")
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{self._AUTH_URL}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._TOKEN_URL,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            return response.json()

    async def fetch_user_profile(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self._USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def create_state(self, ttl: int = 300) -> str:
        state = str(uuid.uuid4())
        await self._redis.setex(f"oauth:state:{state}", ttl, "1")
        return state

    async def validate_and_consume_state(self, state: str) -> None:
        key = f"oauth:state:{state}"
        exists = await self._redis.get(key)
        if not exists:
            raise BadRequestException("Invalid or expired OAuth state")
        await self._redis.delete(key)


async def get_google_oauth_auth_service(
    redis: Redis = Depends(get_redis_client),
    user_service: UserService = Depends(get_user_service),
    user_dao: UserDAO = Depends(get_user_dao),
) -> GoogleOAuthService:
    """
    FastAPI dependency to provide an AuthService instance.

    Args:
        request (Request): FastAPI request object.
        user_dao (UserDAO): DAO injected via dependency.
        redis (Redis): Redis client injected via dependency.

    Returns:
        AuthService: Service instance ready to use in route handlers.
    """
    return GoogleOAuthService(redis=redis, user_service=user_service, user_dao=user_dao)
