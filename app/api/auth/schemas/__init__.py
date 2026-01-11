"""Auth schemas module."""

from app.api.auth.schemas.auth import (
    AuthTokens,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResult,
    OTPVerificationResult,
    PasswordResetRequestResult,
    PasswordResetResult,
    ProtectedRouteResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    ResetPasswordRequest,
    SendOTPRequest,
    SendOTPResponse,
    TokenRefreshResult,
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
