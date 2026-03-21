"""Authentication API Routes"""

from fastapi import APIRouter

from app.api.auth.handlers import (
    forgot_password_handler,
    get_profile_handler,
    login_handler,
    logout_handler,
    protected_route_handler,
    refresh_token_handler,
    register_handler,
    resend_otp_handler,
    reset_password_handler,
    send_otp_handler,
    verify_otp_handler,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Authentication URLs
router.add_api_route("/login", login_handler, methods=["POST"])
router.add_api_route("/logout", logout_handler, methods=["POST"])
router.add_api_route("/refresh", refresh_token_handler, methods=["POST"])
router.add_api_route("/me", get_profile_handler, methods=["GET"])
router.add_api_route("/protected", protected_route_handler, methods=["GET"])

# Register
router.add_api_route(
    "/register",
    register_handler,
    methods=["POST"],
    status_code=201,
    summary="Register",
    description=(
        "Register a new user. "
        "Pass invite_token if arriving from a team invite link — "
        "user will be auto-added to the team after OTP verification."
    ),
)

# OTP
router.add_api_route(
    "/verify-otp",
    verify_otp_handler,
    methods=["POST"],
    summary="Verify OTP",
    description="Verify OTP. If user registered via invite link, auto-joins team after verification.",
)
router.add_api_route("/send-otp", send_otp_handler, methods=["POST"])
router.add_api_route(
    "/resend-otp",
    resend_otp_handler,
    methods=["POST"],
    summary="Resend OTP for Account Verification",
)

# Password Reset URLs
router.add_api_route(
    "/forgot-password",
    forgot_password_handler,
    methods=["POST"],
    summary="Request Password Reset",
    description="Send password reset instructions to user's email",
)
router.add_api_route(
    "/reset-password",
    reset_password_handler,
    methods=["POST"],
    summary="Reset Password",
    description="Reset password using reset token",
)
