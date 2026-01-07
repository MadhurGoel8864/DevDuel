"""
Authentication schemas for user authentication and authorization.
"""

from pydantic import BaseModel, EmailStr

from app.core.enums import UserRole, PlatformType


class UserWithPermissions(BaseModel):
    """
    User object with permissions for authenticated requests.

    This schema represents the current authenticated user with their
    role, permissions, and platform information.
    """

    user_id: str
    email: EmailStr
    role: UserRole
    permissions: list[str]
    is_active: bool
    platform: PlatformType

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class UserProfileResponse(BaseModel):
    """
    Response schema for user profile endpoint.

    Returns the authenticated user's profile information.
    """

    user_id: str
    email: EmailStr
    role: UserRole
    permissions: list[str]
    is_active: bool
    platform: PlatformType

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class ProtectedRouteResponse(BaseModel):
    """
    Response schema for protected route example.

    Demonstrates a protected endpoint response.
    """

    message: str
    authenticated_as: str


class LoginRequest(BaseModel):
    """
    Request schema for user login.

    Contains user credentials and platform information.
    """

    email: EmailStr
    password: str
    platform: PlatformType = PlatformType.WEB

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class LoginResponse(BaseModel):
    """
    Response schema for successful login.

    Returns JWT access token and refresh token for authentication.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class RefreshTokenRequest(BaseModel):
    """
    Request schema for refreshing access token.

    Contains the refresh token to exchange for a new access token.
    """

    refresh_token: str

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class RefreshTokenResponse(BaseModel):
    """
    Response schema for successful token refresh.

    Returns new JWT access token.
    """

    access_token: str
    token_type: str = "bearer"

    class Config:
        """Pydantic configuration."""

        from_attributes = True
