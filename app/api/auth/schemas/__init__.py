"""Auth schemas module."""

from app.api.auth.schemas.auth import (
    LoginRequest,
    LoginResponse,
    ProtectedRouteResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    SendOTPRequest,
    SendOTPResponse,
    UserProfileResponse,
    UserWithPermissions,
    VerifyOTPRequest,
    VerifyOTPResponse,
)

__all__ = ["UserWithPermissions", "UserProfileResponse", "ProtectedRouteResponse"]
