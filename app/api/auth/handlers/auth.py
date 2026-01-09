"""
Authentication handlers.

These handlers implement the authentication endpoints.
"""

import logging
import random

from fastapi import BackgroundTasks, Depends

from app.api.auth.dependencies import get_current_user, get_platform_type
from app.api.auth.schemas import (
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
from app.api.auth.services import AuthService, get_auth_service
from app.api.users.services.users import UserService, get_user_service
from app.core.enums import PlatformType
from app.services.email import email_service
from app.services.email.templates import otp_email_template

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

    return RefreshTokenResponse(access_token=result.access_token)


async def verify_otp_handler(
    request: VerifyOTPRequest,
    auth_service: AuthService = Depends(get_auth_service),
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

    return VerifyOTPResponse(
        message=result.message,
        is_verified=result.is_verified,
        email=result.email,
    )


def send_otp_email_task(email: str, otp: str) -> None:
    """
    Background task to send OTP email.

    This runs asynchronously without blocking the HTTP response.

    Args:
        email: Recipient email address
        otp: The OTP code to send
    """
    try:
        subject, html_body = otp_email_template(otp)
        email_service.send_email(
            to_email=email,
            subject=subject,
            body=html_body,
            html=True,
        )
    except Exception as e:
        # Log error but don't crash the background task
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send OTP email to {email}: {e}")


async def send_otp_handler(
    request: SendOTPRequest,
    background_tasks: BackgroundTasks,
) -> SendOTPResponse:
    """
    Send OTP to user's email (example implementation).

    This is a demonstration of how to integrate the email service.
    In production, you should:
    1. Generate OTP using a secure random generator
    2. Store OTP in Redis with 5-minute TTL
    3. Associate OTP with user email
    4. Send email via background task (as shown here)

    Args:
        request: Email address to send OTP to
        background_tasks: FastAPI background tasks for async email sending

    Returns:
        SendOTPResponse: Confirmation message
    """
    # TODO: Replace with Redis-based OTP storage
    # Example: await redis_client.setex(f"otp:{request.email}", 300, otp)

    # Generate 6-digit OTP (placeholder - use secure random in production)
    otp = str(random.randint(100000, 999999))

    # Add email sending to background tasks (non-blocking)
    background_tasks.add_task(send_otp_email_task, request.email, otp)

    # Return immediately without waiting for email to send
    return SendOTPResponse(
        message="OTP sent successfully. Please check your email.",
        email=request.email,
    )


async def resend_otp_handler(
    request: SendOTPRequest,
    background_tasks: BackgroundTasks,
    user_service: UserService = Depends(get_user_service),
) -> SendOTPResponse:
    """
    Resend OTP to user's email.

    This endpoint delegates to the service layer to validate user existence,
    generate a new OTP, store it in Redis, and send it via email.

    Args:
        request: Email address to resend OTP to
        background_tasks: FastAPI background tasks for async email sending
        user_service: User service for OTP operations

    Returns:
        SendOTPResponse: Confirmation message

    Raises:
        UnauthorizedException: If user with email does not exist
    """
    # Service layer handles all business logic and returns whether OTP was sent
    otp_sent = await user_service.resend_otp(request.email, background_tasks)

    # Return appropriate response based on whether OTP was sent
    if otp_sent:
        return SendOTPResponse(
            message="OTP resent successfully. Please check your email.",
            email=request.email,
        )
    else:
        return SendOTPResponse(
            message="User is already verified. No OTP needed.",
            email=request.email,
        )
