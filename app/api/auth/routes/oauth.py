"""OAuth Authentication API Routes"""

from fastapi import APIRouter

from app.api.auth.handlers import google_callback_handler, google_login_handler

router = APIRouter(prefix="/auth/google", tags=["OAuth Authentication"])

# OAuth Authentication URLs
router.add_api_route(
    "/login",
    google_login_handler,
    methods=["GET"],
    summary="Initiate Google OAuth Login",
    description="Generates a secure state token and returns the Google OAuth authorization URL",
)
router.add_api_route(
    "/callback",
    google_callback_handler,
    methods=["GET"],
    summary="Google OAuth Callback",
    description="Handles the OAuth callback, validates state, and returns access and refresh tokens",
)
