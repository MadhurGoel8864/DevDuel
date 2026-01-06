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
)
from app.api.users.dao.users import UserDAO, get_user_dao
from app.core.security.jwt import create_access_token
from app.core.security.password import verify_password
from app.core.exceptions.auth import UnauthorizedException, ForbiddenException
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

    return LoginResponse(access_token=access_token)
