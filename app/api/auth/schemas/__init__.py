"""Auth schemas module."""

from app.api.auth.schemas.auth import (
    UserWithPermissions,
    UserProfileResponse,
    ProtectedRouteResponse,
    LoginRequest,
    LoginResponse,
)

__all__ = ["UserWithPermissions", "UserProfileResponse", "ProtectedRouteResponse"]
