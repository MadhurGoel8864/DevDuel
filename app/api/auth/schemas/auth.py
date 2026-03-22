"""
Authentication schemas for user authentication and authorization.
"""

from typing import Optional

from pydantic import BaseModel, EmailStr

from app.core.enums import UserRole
from app.core.security.password import PasswordStr


class UserWithPermissions(BaseModel):
    """
    User object with permissions for authenticated requests.

    This schema represents the current authenticated user with their
    role, permissions, and verification status.
    """

    user_id: str
    email: EmailStr
    username: str
    role: UserRole
    permissions: list[str]
    is_active: bool
    is_verified: bool
    profile_img_url: str | None = None

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
    username: str
    role: UserRole
    permissions: list[str]
    is_active: bool
    is_verified: bool
    profile_img_url: str | None = None
    last_login_at: str | None = None

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


# Service-level data models
class AuthTokens(BaseModel):
    """
    Data model for authentication tokens.

    Used by the service layer to return token data.
    """

    access_token: str
    refresh_token: str

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class OTPVerificationResult(BaseModel):
    """
    Data model for OTP verification result.

    Used by the service layer to return verification status.
    """

    message: str
    is_verified: bool
    email: EmailStr

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class TokenRefreshResult(BaseModel):
    """
    Data model for token refresh result.

    Used by the service layer to return new access token.
    """

    access_token: str
    refresh_token: str

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class PasswordResetRequestResult(BaseModel):
    """
    Data model for password reset request result.

    Used by the service layer to return reset token data for email sending.
    """

    user_id: str
    email: str
    reset_token: str

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class PasswordResetResult(BaseModel):
    """
    Data model for password reset completion result.

    Used by the service layer to return success message.
    """

    message: str

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class LoginRequest(BaseModel):
    """
    Request schema for user login.

    Contains user credentials.
    """

    email: EmailStr
    password: str

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
    refresh_token: str
    token_type: str = "bearer"

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class VerifyOTPRequest(BaseModel):
    """
    Request schema for OTP verification.

    Contains the user's email and OTP code to verify.
    """

    email: EmailStr
    otp: str

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class VerifyOTPResponse(BaseModel):
    """
    Response schema for successful OTP verification.

    Returns success message and verification status.
    """

    message: str
    is_verified: bool
    email: EmailStr

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class SendOTPRequest(BaseModel):
    """Request schema for sending OTP."""

    email: EmailStr


class SendOTPResponse(BaseModel):
    """Response schema for OTP sending."""

    message: str
    email: str


class ForgotPasswordRequest(BaseModel):
    """
    Request schema for initiating password reset.

    Contains the user's email address to send password reset instructions.
    """

    email: EmailStr

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class ForgotPasswordResponse(BaseModel):
    """
    Response schema for password reset request.

    Returns confirmation that reset instructions were sent.
    """

    message: str
    email: str

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class ResetPasswordRequest(BaseModel):
    """
    Request schema for resetting password with token.

    Contains the reset token and new password.
    """

    token: str
    new_password: PasswordStr

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class LogoutRequest(BaseModel):
    """
    Request schema for user logout.

    Contains the refresh token to validate and blacklist along with access token.
    """

    refresh_token: str

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class LogoutResult(BaseModel):
    """
    Data model for logout result.

    Used by the service layer to return logout success message.
    """

    message: str

    class Config:
        """Pydantic configuration."""


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr
    password: PasswordStr
    full_name: str
    invite_token: Optional[str] = None

    class Config:
        from_attributes = True


class RegisterResponse(BaseModel):
    """Response schema for successful registration."""

    message: str
    email: str

    class Config:
        from_attributes = True
