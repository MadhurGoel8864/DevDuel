"""
Authentication dependencies for FastAPI.

This module provides authentication dependencies for protecting routes
and extracting the current authenticated user.
"""

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.api.auth.schemas import UserWithPermissions
from app.core.enums import TokenType, UserRole, PlatformType
from app.core.security.jwt import decode_token, TokenExpiredError, InvalidTokenError
from app.core.exceptions.auth import (
    AuthenticationRequiredException,
    InvalidAccessTokenException,
    InvalidTokenTypeException,
)


# HTTP Bearer scheme for Swagger UI "Authorize" button
security = HTTPBearer(
    scheme_name="Bearer", description="Enter your JWT access token", auto_error=False
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserWithPermissions:
    """
    Get the current authenticated user from JWT access token.

    This dependency:
    - Extracts the Bearer token from Authorization header
    - Decodes and validates the token
    - Enforces that the token is an ACCESS token (not REFRESH)
    - Returns a UserWithPermissions object

    Args:
        credentials: HTTP Bearer credentials from the Authorization header

    Returns:
        UserWithPermissions: The authenticated user with permissions

    Raises:
        AuthenticationRequiredException: If no credentials are provided
        InvalidAccessTokenException: If token is invalid or expired
        InvalidTokenTypeException: If token type is not ACCESS
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

        # TODO: Create and return UserWithPermissions object
        # Note: Permissions are not fetched from DB yet (as per Step 2 requirements)
        return UserWithPermissions(
            user_id=user_id,
            email=email,
            role=UserRole.USER,  # Default role
            permissions=[],  # Empty permissions for now
            is_active=True,  # Default to active
            platform=PlatformType.WEB,  # Default platform
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
