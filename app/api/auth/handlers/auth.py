"""
Authentication handlers.

These handlers implement the authentication endpoints.
"""

import logging
import random

from arq.connections import ArqRedis
from fastapi import Depends

from app.api.auth.dependencies import (
    get_current_user,
    get_logout_tokens,
    get_platform_type,
)
from app.api.auth.schemas import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    ProtectedRouteResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    SendOTPRequest,
    SendOTPResponse,
    UserProfileResponse,
    UserWithPermissions,
    VerifyOTPRequest,
    VerifyOTPResponse,
)
from app.api.auth.services import AuthService, get_auth_service
from app.api.common.responses import MessageResponse
from app.api.teams.services.team_invites import (
    TeamInviteService,
    get_team_invite_service,
)
from app.api.users.schemas.users import UserCreateData
from app.api.users.services.users import UserService, get_user_service
from app.core.arq_pool import get_arq_pool_dep
from app.core.config import settings
from app.core.enums import PlatformType

logger = logging.getLogger(__name__)


async def get_profile_handler(
    current_user: UserWithPermissions = Depends(get_current_user),
    platform_type: PlatformType = Depends(get_platform_type),
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
    logger.info(f"Platform type: {platform_type}")
    return UserProfileResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        role=current_user.role,
        username=current_user.username,
        permissions=current_user.permissions,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
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
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """
    Authenticate user and issue JWT access token.

    This endpoint validates user credentials against the database
    and returns a JWT token for authenticated requests.

    Args:
        request: Login credentials (email, password)
        auth_service: Auth service for authentication operations

    Returns:
        LoginResponse: JWT access token and refresh token

    Raises:
        UnauthorizedException: If credentials are invalid
        ForbiddenException: If user account is inactive or not verified
    """
    # Delegate authentication to service layer
    tokens = await auth_service.authenticate_user(
        email=request.email,
        password=request.password,
    )

    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


async def refresh_token_handler(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> RefreshTokenResponse:
    """
    Refresh access token using a valid refresh token.

    This endpoint exchanges a valid refresh token for a new access token
    without requiring re-authentication.

    Args:
        request: Refresh token request containing the refresh token
        auth_service: Auth service for token operations

    Returns:
        RefreshTokenResponse: New JWT access token and token type

    Raises:
        InvalidAccessTokenException: If token is expired or invalid
        InvalidTokenTypeException: If token type is not "refresh"
    """
    # Delegate token refresh to service layer
    result = await auth_service.refresh_access_token(request.refresh_token)

    return RefreshTokenResponse(
        access_token=result.access_token, refresh_token=result.refresh_token
    )


async def register_handler(
    request: RegisterRequest,
    user_service: UserService = Depends(get_user_service),
    invite_service: TeamInviteService = Depends(get_team_invite_service),
    arq_pool: ArqRedis = Depends(get_arq_pool_dep),
) -> RegisterResponse:
    """
    Register a new user.

    If invite_token is present:
      1. Token is validated upfront — if invalid/expired, entire request is rejected
         so no orphaned user account is created.
      2. User is created normally and OTP is enqueued via ARQ.
      3. invite_token is stored in Redis as pending_team_join:{user_id}
      4. When user verifies OTP → they are automatically added to the team.
    """
    if request.invite_token:
        await invite_service.validate_token(request.invite_token)

    user_data = UserCreateData(
        email=request.email,
        password=request.password,
        full_name=request.full_name,
    )
    new_user, otp = await user_service.create_user(user_data=user_data)

    await arq_pool.enqueue_job("send_otp_email_task", email=new_user.email, otp=otp)
    logger.info(f"OTP email enqueued for {new_user.email}")

    if request.invite_token:
        await invite_service.store_pending_join(
            user_id=new_user.id,
            invite_token=request.invite_token,
        )
        logger.info(f"Pending team join stored for new user {new_user.id} via invite token")

    return RegisterResponse(
        message=(
            "Registration successful. Please check your email to verify your account."
            + (
                " You will be added to the team after verification."
                if request.invite_token
                else ""
            )
        ),
        email=request.email,
    )


async def verify_otp_handler(
    request: VerifyOTPRequest,
    auth_service: AuthService = Depends(get_auth_service),
    invite_service: TeamInviteService = Depends(get_team_invite_service),
) -> VerifyOTPResponse:
    """
    Verify OTP and update user verification status.

    This endpoint validates the OTP from Redis against the provided code
    and sets the user's is_verified field to True upon successful verification.

    Args:
        request: OTP verification request containing email and OTP code
        auth_service: Auth service for OTP verification operations

    Returns:
        VerifyOTPResponse: Verification success message and status

    Raises:
        UnauthorizedException: If user not found or OTP is invalid/expired
    """
    # Delegate OTP verification to service layer
    result = await auth_service.verify_user_otp(
        email=request.email,
        otp=request.otp,
    )

    # If verification succeeded, check for pending team join
    # (user registered via invite link — auto-add them to the team now)
    if result.is_verified:
        user = await auth_service._user_dao.get_by_email(request.email)
        if user:
            await invite_service.consume_pending_join(
                user_id=user.id,
                verified_email=user.email,
            )

    return VerifyOTPResponse(
        message=result.message,
        is_verified=result.is_verified,
        email=result.email,
    )


async def send_otp_handler(
    request: SendOTPRequest,
    arq_pool: ArqRedis = Depends(get_arq_pool_dep),
) -> SendOTPResponse:
    """Send OTP to user's email (example/test endpoint)."""
    otp = str(random.randint(100000, 999999))
    await arq_pool.enqueue_job("send_otp_email_task", email=request.email, otp=otp)
    return SendOTPResponse(
        message="OTP sent successfully. Please check your email.",
        email=request.email,
    )


async def resend_otp_handler(
    request: SendOTPRequest,
    user_service: UserService = Depends(get_user_service),
    arq_pool: ArqRedis = Depends(get_arq_pool_dep),
) -> SendOTPResponse:
    """Resend OTP to user's email."""
    otp_sent, otp = await user_service.resend_otp(request.email)

    if otp_sent:
        await arq_pool.enqueue_job("send_otp_email_task", email=request.email, otp=otp)
        return SendOTPResponse(
            message="OTP resent successfully. Please check your email.",
            email=request.email,
        )
    else:
        return SendOTPResponse(
            message="User is already verified. No OTP needed.",
            email=request.email,
        )


async def forgot_password_handler(
    request: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
    arq_pool: ArqRedis = Depends(get_arq_pool_dep),
) -> ForgotPasswordResponse:
    """Initiate password reset — generate token, enqueue reset email."""
    result = await auth_service.request_password_reset(request.email)
    reset_link = f"{settings.FRONTEND_RESET_PASSWORD_URL}?token={result.reset_token}"

    await arq_pool.enqueue_job(
        "send_password_reset_task",
        email=result.email,
        reset_link=reset_link,
    )

    return ForgotPasswordResponse(
        message="Password reset instructions have been sent to your email.",
        email=request.email,
    )


async def reset_password_handler(
    request: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """
    Reset user password using reset token.

    Validates token, updates password, and deletes token.

    Args:
        request: Reset token and new password
        auth_service: Auth service for password reset operations

    Returns:
        ResetPasswordResponse: Success message

    Raises:
        UnauthorizedException: If token is invalid or expired
    """
    # Delegate to service layer
    result = await auth_service.reset_password(
        token=request.token,
        new_password=request.new_password,
    )

    return MessageResponse(message=result.message)


async def logout_handler(
    request: LogoutRequest,
    access_token: str = Depends(get_logout_tokens),
    auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """
    Logout user by blacklisting both access and refresh tokens.

    This endpoint:
    - Validates access token from Authorization header
    - Validates refresh token from request body
    - Blacklists both tokens in Redis

    Args:
        request: Logout request containing the refresh token
        access_token: Access token extracted from Authorization header
        auth_service: Auth service for logout operations

    Returns:
        MessageResponse: Success message

    Raises:
        InvalidAccessTokenException: If tokens are invalid or expired
        InvalidTokenTypeException: If token types are incorrect
    """
    # Delegate to service layer to blacklist both tokens
    result = await auth_service.logout(access_token, request.refresh_token)

    return MessageResponse(message=result.message)
