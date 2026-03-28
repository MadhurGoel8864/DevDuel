"""Auth Service Layer"""

import logging
import time
import uuid

from fastapi import Depends
from redis.asyncio import Redis

from app.api.auth.schemas import (
    AuthTokens,
    LogoutResult,
    OTPVerificationResult,
    PasswordResetRequestResult,
    PasswordResetResult,
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
from app.core.config import settings
from app.core.redis import get_redis_client
from app.core.security.jwt import (
    InvalidTokenError,
    TokenExpiredError,
    blacklist_jti,
    create_access_token,
    create_refresh_token,
    decode_token,
    is_jti_blacklisted,
)
from app.core.security.password import hash_password, verify_password

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

        # Check if account was created via OAuth (Google) and has no password set
        if not user.password_hash and user.auth_provider == "google":
            logger.warning(
                f"Authentication failed: Account created via Google OAuth for {email}"
            )
            raise UnauthorizedException(
                message="This account was created using Google Sign-In. "
                "Please sign in with Google or set a password for your account."
            )

        # Validate password hash exists for local accounts
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
            "is_organizer": user.is_organizer,
        }

        # Generate JWT tokens
        access_token = create_access_token(payload=token_payload)
        refresh_token = create_refresh_token(payload=token_payload)

        # Update last login timestamp
        try:
            await self._user_dao.update_last_login(user.id)
            logger.info(f"Updated last_login_at for user {email}")
        except Exception as e:
            # Log error but don't fail authentication
            logger.error(f"Failed to update last_login_at for user {email}: {e}")

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

        # Allow dummy OTP in non-production environments for easier testing
        DUMMY_OTP = "000000"
        redis_key = None
        if settings.env != "production" and otp == DUMMY_OTP:
            logger.warning(
                f"Dummy OTP accepted for {email} (env={settings.env}). "
                "This is NOT allowed in production."
            )
        else:
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
        if redis_key:
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

        jti = payload.get("jti")

        if not isinstance(jti, str):
            raise InvalidAccessTokenException(message="Invalid token payload")

        if await is_jti_blacklisted(jti):
            logger.warning(f"Token refresh failed: JTI {jti} is blacklisted")
            raise InvalidAccessTokenException(message="Refresh Token is blacklisted")

        # Calculate remaining TTLs
        now = int(time.time())
        refresh_ttl = payload["exp"] - now
        await blacklist_jti(jti, refresh_ttl)

        # Extract user information from refresh token payload
        user_id = payload.get("sub")
        email = payload.get("email")

        # Fetch latest is_organizer from DB so revoked organizer status takes effect
        user = await self._user_dao.get_by_id(user_id)
        is_organizer = user.is_organizer if user else False

        # Create new access token payload
        new_token_payload = {
            "sub": user_id,
            "email": email,
            "is_organizer": is_organizer,
        }

        # Generate new JWT access token
        access_token = create_access_token(payload=new_token_payload)
        refresh_token = create_refresh_token(payload=new_token_payload)

        logger.info(f"Access token refreshed successfully for user {email}")

        return TokenRefreshResult(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def request_password_reset(self, email: str) -> PasswordResetRequestResult:
        """
        Request password reset and send reset token via email.

        Business logic:
        - Validates user exists and is active
        - Generates secure reset token (UUID)
        - Stores token in Redis with 15-minute TTL
        - Returns success message (email sending handled by handler)

        Args:
            email (str): User email address

        Returns:
            PasswordResetRequestResult: Contains user_id, email, and reset_token for email sending

        Raises:
            UnauthorizedException: If user not found
            ForbiddenException: If user account is inactive
        """

        logger.info(f"Processing password reset request for email: {email}")

        # Fetch user from database by email
        user = await self._user_dao.get_by_email(email)

        # Validate user exists
        if not user:
            logger.warning(f"Password reset failed: User not found for email {email}")
            raise UnauthorizedException(message="User not found")

        # Validate user account is active
        if not user.is_active:
            logger.warning(f"Password reset failed: User account inactive for {email}")
            raise ForbiddenException(message="User account is inactive")

        # Generate secure reset token
        reset_token = str(uuid.uuid4())

        # Store token in Redis with 15-minute TTL (900 seconds)
        redis_key = f"password_reset:{reset_token}"
        await self._redis.setex(redis_key, 900, user.id)

        logger.info(f"Password reset token generated for user {email}")

        return PasswordResetRequestResult(
            user_id=user.id,
            email=email,
            reset_token=reset_token,
        )

    async def reset_password(
        self, token: str, new_password: str
    ) -> PasswordResetResult:
        """
        Reset user password using reset token.

        Business logic:
        - Validates reset token exists in Redis
        - Retrieves user ID from token
        - Hashes new password
        - Updates password in database
        - Deletes token from Redis

        Args:
            token (str): Password reset token
            new_password (str): New password to set

        Returns:
            PasswordResetResult: Success message

        Raises:
            UnauthorizedException: If token is invalid or expired
        """
        logger.info("Processing password reset with token")

        # Retrieve user ID from Redis using token
        redis_key = f"password_reset:{token}"
        user_id = await self._redis.get(redis_key)

        # Validate token exists in Redis
        if not user_id:
            logger.warning("Password reset failed: Invalid or expired token")
            raise UnauthorizedException(
                message="Invalid or expired reset token. Please request a new password reset."
            )

        # Hash new password
        new_password_hash = hash_password(new_password)

        # Update password in database
        try:
            await self._user_dao.update_password(user_id, new_password_hash)
        except Exception as e:
            logger.error(f"Failed to update password for user {user_id}: {e}")
            raise UnauthorizedException(message="Failed to reset password")

        # Delete token from Redis after successful password reset
        await self._redis.delete(redis_key)

        logger.info(f"Password reset successfully for user {user_id}")

        return PasswordResetResult(message="Password reset successfully")

    async def logout(self, access_token: str, refresh_token: str) -> LogoutResult:
        """
        Logout user by blacklisting both access and refresh tokens.

        Business logic:
        - Validates refresh token
        - Extracts JTI from both tokens
        - Blacklists both tokens in Redis with remaining TTL

        Args:
            access_token (str): The access token to blacklist
            refresh_token (str): The refresh token to validate and blacklist

        Returns:
            LogoutResult: Success message

        Raises:
            InvalidAccessTokenException: If tokens are expired or invalid
            InvalidTokenTypeException: If refresh token type is not REFRESH
        """
        logger.info("Processing logout request")

        try:
            access_payload = decode_token(access_token)
            refresh_payload = decode_token(refresh_token)

            # Validate refresh token type
            if refresh_payload.get("type") != TokenType.REFRESH.value:
                logger.warning("Logout failed: Invalid refresh token type")
                raise InvalidTokenTypeException(message="Refresh token required")

            # Extract required fields
            access_jti = access_payload.get("jti")
            refresh_jti = refresh_payload.get("jti")

            if not access_jti or not refresh_jti:
                raise InvalidTokenError("Token does not contain JTI")

            # Calculate remaining TTLs
            now = int(time.time())
            access_ttl = access_payload["exp"] - now
            refresh_ttl = refresh_payload["exp"] - now

            # Blacklist both tokens
            await blacklist_jti(access_jti, access_ttl)
            await blacklist_jti(refresh_jti, refresh_ttl)

        except TokenExpiredError as e:
            logger.warning(f"Logout failed: {str(e)}")
            raise InvalidAccessTokenException(message="Token has expired")
        except InvalidTokenError as e:
            logger.warning(f"Logout failed: {str(e)}")
            raise InvalidAccessTokenException(message="Invalid token")
        except InvalidTokenTypeException:
            # Re-raise token type exception
            raise

        logger.info("User logged out successfully - both tokens blacklisted")

        return LogoutResult(message="Logged out successfully")


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
