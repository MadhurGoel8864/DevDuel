"""Auth Service Layer"""

import logging

from fastapi import Depends
from redis.asyncio import Redis

from app.api.auth.schemas.auth import (
    AuthTokens,
    OTPVerificationResult,
    TokenRefreshResult,
)
from app.api.users.dao.users import UserDAO, get_user_dao
from app.core.enums import TokenType
from app.core.exceptions.auth import (
    ForbiddenException,
    InvalidAccessTokenException,
    InvalidTokenTypeException,
    UnauthorizedException,
)
from app.core.redis import get_redis_client
from app.core.security.jwt import (
    InvalidTokenError,
    TokenExpiredError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.security.password import verify_password

logger = logging.getLogger(__name__)


class AuthService:
    """
    Service class to handle business logic for authentication operations.

    Attributes:
        _user_dao (UserDAO): DAO instance for interacting with the user database.
        _redis (Redis): Redis client for OTP storage/retrieval.
    """

    def __init__(self, user_dao: UserDAO, redis: Redis):
        """
        Initialize the service with UserDAO and Redis instances.

        Args:
            user_dao (UserDAO): DAO for performing database operations.
            redis (Redis): Redis client for caching operations.
        """
        self._user_dao = user_dao
        self._redis = redis

    async def authenticate_user(self, email: str, password: str) -> AuthTokens:
        """
        Authenticate user and generate JWT tokens.

        Business logic:
        - Validates user credentials
        - Checks account status (active and verified)
        - Generates access and refresh tokens

        Args:
            email (str): User email address
            password (str): User password

        Returns:
            AuthTokens: Pydantic model containing access_token and refresh_token

        Raises:
            UnauthorizedException: If credentials are invalid
            ForbiddenException: If user account is inactive or not verified
        """
        logger.info(f"Authenticating user with email: {email}")

        # Fetch user from database by email
        user = await self._user_dao.get_by_email(email)

        # Validate user exists
        if not user:
            logger.warning(f"Authentication failed: User not found for email {email}")
            raise UnauthorizedException(message="Invalid credentials")

        # Validate user account is active
        if not user.is_active:
            logger.warning(f"Authentication failed: User account inactive for {email}")
            raise ForbiddenException(message="User account is inactive")

        # Validate user account is verified
        if not user.is_verified:
            logger.warning(
                f"Authentication failed: User account not verified for {email}"
            )
            raise ForbiddenException(
                message="Please verify your account before logging in"
            )

        # Validate password hash exists
        if not user.password_hash:
            logger.warning(f"Authentication failed: No password hash for {email}")
            raise UnauthorizedException(message="Invalid credentials")

        # Verify password
        if not verify_password(password, user.password_hash):
            logger.warning(f"Authentication failed: Invalid password for {email}")
            raise UnauthorizedException(message="Invalid credentials")

        # Create JWT token payload with user data
        token_payload = {
            "sub": user.id,
            "email": user.email,
        }

        # Generate JWT tokens
        access_token = create_access_token(payload=token_payload)
        refresh_token = create_refresh_token(payload=token_payload)

        logger.info(f"User {email} authenticated successfully")

        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def verify_user_otp(self, email: str, otp: str) -> OTPVerificationResult:
        """
        Verify OTP and update user verification status.

        Business logic:
        - Validates OTP from Redis
        - Updates user verification status
        - Cleans up Redis after successful verification

        Args:
            email (str): User email address
            otp (str): OTP code to verify

        Returns:
            OTPVerificationResult: Pydantic model containing verification status and message

        Raises:
            UnauthorizedException: If user not found or OTP is invalid/expired
        """
        logger.info(f"Verifying OTP for user: {email}")

        # Get user from database
        user = await self._user_dao.get_by_email(email)
        if not user:
            logger.warning(f"OTP verification failed: User not found for {email}")
            raise UnauthorizedException(message="User not found")

        # Check if user is already verified
        if user.is_verified:
            logger.info(f"User {email} is already verified")
            return OTPVerificationResult(
                message="User is already verified",
                is_verified=True,
                email=email,
            )

        # Retrieve OTP from Redis using user ID as key
        redis_key = f"otp:user:{user.id}"
        stored_otp = await self._redis.get(redis_key)

        # Validate OTP exists in Redis
        if not stored_otp:
            logger.warning(
                f"OTP verification failed: OTP expired or not found for {email}"
            )
            raise UnauthorizedException(message="OTP has expired or does not exist")

        # Validate OTP matches
        if stored_otp != otp:
            logger.warning(f"OTP verification failed: Invalid OTP for {email}")
            raise UnauthorizedException(message="Invalid OTP")

        # Update user verification status
        verified_user = await self._user_dao.verify_user(email)
        if not verified_user:
            logger.error(f"Failed to update verification status for {email}")
            raise UnauthorizedException(message="Failed to verify user")

        # Delete OTP from Redis after successful verification
        await self._redis.delete(redis_key)

        logger.info(f"User {email} verified successfully")

        return OTPVerificationResult(
            message="User verified successfully",
            is_verified=True,
            email=email,
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenRefreshResult:
        """
        Refresh access token using a valid refresh token.

        Business logic:
        - Validates refresh token
        - Checks token type is 'refresh'
        - Generates new access token

        Args:
            refresh_token (str): The refresh token

        Returns:
            TokenRefreshResult: Pydantic model containing new access_token

        Raises:
            InvalidAccessTokenException: If token is expired or invalid
            InvalidTokenTypeException: If token type is not 'refresh'
        """
        logger.info("Processing refresh token request")

        try:
            # Decode and validate the refresh token
            payload = decode_token(refresh_token)
        except (TokenExpiredError, InvalidTokenError) as e:
            logger.warning(f"Token refresh failed: {str(e)}")
            raise InvalidAccessTokenException(
                message="Invalid or expired refresh token"
            )

        # Enforce token type must be "refresh"
        token_type = payload.get("type")
        if token_type != TokenType.REFRESH.value:
            logger.warning(f"Token refresh failed: Invalid token type {token_type}")
            raise InvalidTokenTypeException(message="Refresh token required")

        # Extract user information from refresh token payload
        user_id = payload.get("sub")
        email = payload.get("email")

        # Create new access token payload
        new_token_payload = {
            "sub": user_id,
            "email": email,
        }

        # Generate new JWT access token
        access_token = create_access_token(payload=new_token_payload)

        logger.info(f"Access token refreshed successfully for user {email}")

        return TokenRefreshResult(
            access_token=access_token,
        )


async def get_auth_service(
    user_dao: UserDAO = Depends(get_user_dao),
    redis: Redis = Depends(get_redis_client),
) -> AuthService:
    """
    FastAPI dependency to provide an AuthService instance.

    Args:
        request (Request): FastAPI request object.
        user_dao (UserDAO): DAO injected via dependency.
        redis (Redis): Redis client injected via dependency.

    Returns:
        AuthService: Service instance ready to use in route handlers.
    """
    return AuthService(user_dao=user_dao, redis=redis)
