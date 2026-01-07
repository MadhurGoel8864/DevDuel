"""
Authentication dependencies for FastAPI.

This module provides authentication dependencies for protecting routes
and extracting the current authenticated user.
"""

from fastapi import Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.api.auth.schemas import UserWithPermissions
from app.api.users.dao.users import UserDAO, get_user_dao
from app.core.enums import TokenType, UserRole, PlatformType
from app.core.constants import PLATFORM_TYPE_HEADER
from app.core.security.jwt import decode_token, TokenExpiredError, InvalidTokenError
from app.core.exceptions.auth import (
    AuthenticationRequiredException,
    InvalidAccessTokenException,
    InvalidTokenTypeException,
    ForbiddenException,
)


# HTTP Bearer scheme for Swagger UI "Authorize" button
security = HTTPBearer(
    scheme_name="Bearer", description="Enter your JWT access token", auto_error=False
)


async def get_platform_type(
    platform_type: PlatformType = Header(
        default=PlatformType.WEB.value, alias=PLATFORM_TYPE_HEADER
    )
) -> PlatformType:
    """
    Dependency to extract platform type from HTTP header.

    Extracts platform type from X-Platform-Type header.
    Defaults to WEB if header is not provided.

    Args:
        platform_type: Platform type from header (default: "web")

    Returns:
        PlatformType: Platform type enum

    Raises:
        ValueError: If invalid platform type is provided
    """
    try:
        return PlatformType(platform_type)
    except ValueError:
        # If invalid platform type, default to WEB
        return PlatformType.WEB


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_dao: UserDAO = Depends(get_user_dao),
) -> UserWithPermissions:
    """
    Get the current authenticated user from JWT access token.

    This dependency:
    - Extracts the Bearer token from Authorization header
    - Decodes and validates the token
    - Enforces that the token is an ACCESS token (not REFRESH)
    - Verifies that the user account is verified (is_verified=True)
    - Returns a UserWithPermissions object

    Args:
        credentials: HTTP Bearer credentials from the Authorization header
        user_dao: User data access object for database operations

    Returns:
        UserWithPermissions: The authenticated user with permissions

    Raises:
        AuthenticationRequiredException: If no credentials are provided
        InvalidAccessTokenException: If token is invalid or expired
        InvalidTokenTypeException: If token type is not ACCESS
        ForbiddenException: If user account is not verified
    """
    # Check if credentials are provided
    if not credentials:
        raise AuthenticationRequiredException()

    token = credentials.credentials

    try:
        # Decode the token using the JWT utility
        payload = decode_token(token)

        # Enforce ACCESS token type
        token_type = payload.get("type")
        if token_type != TokenType.ACCESS.value:
            raise InvalidTokenTypeException()

        # Extract user information from payload
        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id or not email:
            raise InvalidAccessTokenException(message="Invalid token payload")

        # Fetch user from database to check verification status
        user = await user_dao.get_by_id(user_id)
        if not user:
            raise InvalidAccessTokenException(message="User not found")

        # Check if user is verified
        if not user.is_verified:
            raise ForbiddenException(
                message="Account not verified. Please verify your account with OTP."
            )

        # Check if user is active
        if not user.is_active:
            raise ForbiddenException(message="User account is inactive")

        # Return UserWithPermissions object with real user data
        return UserWithPermissions(
            user_id=user.id,
            email=user.email,
            role=UserRole.USER,  # Default role
            permissions=[],  # Empty permissions for now
            is_active=user.is_active,
            is_verified=user.is_verified,
        )

    except TokenExpiredError:
        # Token has expired
        raise InvalidAccessTokenException(message="Token has expired")

    except InvalidTokenError:
        # Invalid token signature or malformed token
        raise InvalidAccessTokenException(message="Invalid token")

    except (
        AuthenticationRequiredException,
        InvalidAccessTokenException,
        InvalidTokenTypeException,
    ):
        # Re-raise our custom exceptions
        raise

    except Exception:
        # Catch any other unexpected errors without leaking details
        raise
