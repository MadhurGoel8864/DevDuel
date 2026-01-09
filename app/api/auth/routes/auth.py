"""Authentication API Routes"""

from fastapi import APIRouter

from app.api.auth.handlers import (
    get_profile_handler,
    login_handler,
    protected_route_handler,
    refresh_token_handler,
    resend_otp_handler,
    send_otp_handler,
    verify_otp_handler,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Authentication URLs
router.add_api_route("/login", login_handler, methods=["POST"])
router.add_api_route("/refresh", refresh_token_handler, methods=["POST"])
router.add_api_route("/verify-otp", verify_otp_handler, methods=["POST"])
router.add_api_route("/me", get_profile_handler, methods=["GET"])
router.add_api_route("/protected", protected_route_handler, methods=["GET"])

# OTP Email Example (demonstrates email service integration)
router.add_api_route("/send-otp", send_otp_handler, methods=["POST"])  # TODO: Remove 
router.add_api_route("/resend-otp", resend_otp_handler, methods=["POST"])
