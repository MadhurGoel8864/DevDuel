"""Auth handlers module."""

from app.api.auth.handlers.auth import (
    get_profile_handler,
    protected_route_handler,
    login_handler,
    refresh_token_handler,
    verify_otp_handler,
)
