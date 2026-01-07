"""
Authentication handlers.

These handlers implement the authentication endpoints.
"""

from app.api.auth.dependencies import get_current_user
from app.api.auth.schemas import (
    UserWithPermissions,
    UserProfileResponse,
    ProtectedRouteResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
)
from app.api.users.dao.users import UserDAO, get_user_dao
from app.core.security.jwt import create_access_token, create_refresh_token, decode_token
from app.core.security.password import verify_password
from app.core.exceptions.auth import (
    UnauthorizedException,
    ForbiddenException,
    InvalidAccessTokenException,
    InvalidTokenTypeException,
)
from app.core.enums import TokenType, PlatformType
from app.core.security.jwt import TokenExpiredError, InvalidTokenError
from fastapi import Depends


async def get_profile_handler(
    current_user: UserWithPermissions = Depends(get_current_user),
) -> UserProfileResponse:
    """
    Get current authenticated user information.

    This endpoint requires a valid JWT access token.
    Use the 🔒 Authorize button in Swagger UI to test.

    Args:
        current_user: The authenticated user from JWT token

    Returns:
        UserProfileResponse: Current user information
    """
    return UserProfileResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        role=current_user.role,
        permissions=current_user.permissions,
        is_active=current_user.is_active,
        platform=current_user.platform,
    )


async def protected_route_handler(
    current_user: UserWithPermissions = Depends(get_current_user),
) -> ProtectedRouteResponse:
    """
    Example protected route.

    This endpoint demonstrates how to protect routes with authentication.

    Args:
        current_user: The authenticated user from JWT token

    Returns:
        ProtectedRouteResponse: Success message with user info
    """
    return ProtectedRouteResponse(
        message="This is a protected route",
        authenticated_as=current_user.email,
    )


async def login_handler(
    request: LoginRequest,
    user_dao: UserDAO = Depends(get_user_dao),
) -> LoginResponse:
    """
    Authenticate user and issue JWT access token.

    This endpoint validates user credentials against the database
    and returns a JWT token for authenticated requests.

    Args:
        request: Login credentials (email, password, platform)
        user_dao: User data access object for database operations

    Returns:
        LoginResponse: JWT access token and token type

    Raises:
        UnauthorizedException: If credentials are invalid
        ForbiddenException: If user account is inactive
    """
    # Fetch user from database by email
    user = await user_dao.get_by_email(request.email)
    print("user: ", user)

    # Validate user exists
    if not user:
        raise UnauthorizedException(message="Invalid credentials")

    # Validate user account is active
    if not user.is_active:
        raise ForbiddenException(message="User account is inactive")

    # Validate password hash exists
    if not user.password_hash:
        raise UnauthorizedException(message="Invalid credentials")

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise UnauthorizedException(message="Invalid credentials")

    # Create JWT token payload with real user data
    token_payload = {
        "sub": user.id,
        "email": user.email,
        "platform": request.platform.value,
    }

    # Generate JWT access token
    access_token = create_access_token(payload=token_payload)

    # Generate JWT refresh token
    refresh_token = create_refresh_token(payload=token_payload)

    return LoginResponse(access_token=access_token, refresh_token=refresh_token)


async def refresh_token_handler(
    request: RefreshTokenRequest,
) -> RefreshTokenResponse:
    """
    Refresh access token using a valid refresh token.

    This endpoint exchanges a valid refresh token for a new access token
    without requiring re-authentication.

    Args:
        request: Refresh token request containing the refresh token

    Returns:
        RefreshTokenResponse: New JWT access token and token type

    Raises:
        InvalidAccessTokenException: If token is expired or invalid
        InvalidTokenTypeException: If token type is not "refresh"
    """
    try:
        # Decode and validate the refresh token
        payload = decode_token(request.refresh_token)
    except (TokenExpiredError, InvalidTokenError):
        # Token is expired or invalid
        raise InvalidAccessTokenException(message="Invalid or expired refresh token")

    # Enforce token type must be "refresh"
    token_type = payload.get("type")
    if token_type != TokenType.REFRESH.value:
        raise InvalidTokenTypeException(message="Refresh token required")

    # Extract user information from refresh token payload
    user_id = payload.get("sub")
    email = payload.get("email")
    platform = payload.get("platform", PlatformType.WEB.value)

    # Create new access token payload
    new_token_payload = {
        "sub": user_id,
        "email": email,
        "platform": platform,
    }

    # Generate new JWT access token
    access_token = create_access_token(payload=new_token_payload)

    return RefreshTokenResponse(access_token=access_token)
