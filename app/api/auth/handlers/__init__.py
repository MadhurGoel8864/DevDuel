"""Auth handlers module."""

from app.api.auth.handlers.auth import (
    forgot_password_handler,
    get_profile_handler,
    login_handler,
    logout_handler,
    protected_route_handler,
    refresh_token_handler,
    resend_otp_handler,
    reset_password_handler,
    send_otp_handler,
    verify_otp_handler,
)
from app.api.auth.handlers.oauth import google_callback_handler, google_login_handler
