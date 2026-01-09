"""Auth handlers module."""

from app.api.auth.handlers.auth import (
    get_profile_handler,
    login_handler,
    protected_route_handler,
    refresh_token_handler,
    resend_otp_handler,
    send_otp_handler,
    verify_otp_handler,
)
