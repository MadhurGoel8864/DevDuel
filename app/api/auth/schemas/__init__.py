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
from app.api.auth.schemas.oauth import GoogleCallbackResponse, GoogleLoginResponse

__all__ = [
    "UserWithPermissions",
    "UserProfileResponse",
    "ProtectedRouteResponse",
    "GoogleLoginResponse",
    "GoogleCallbackResponse",
]
