"""OAuth Authentication API Routes"""

from fastapi import APIRouter, Depends

from app.api.auth.handlers import google_callback_handler, google_login_handler
from app.core.rate_limit import rate_limit

router = APIRouter(prefix="/auth/google", tags=["OAuth Authentication"])

# OAuth Authentication URLs
router.add_api_route(
    "/login",
    google_login_handler,
    methods=["GET"],
    summary="Initiate Google OAuth Login",
    description="Generates a secure state token and returns the Google OAuth authorization URL",
    # Each login attempt stores a state token in Redis (300s TTL). Limit prevents
    # Redis flooding via unbounded state-token creation.
    dependencies=[Depends(rate_limit("auth:google:login", 10, 60))],
)
router.add_api_route(
    "/callback",
    google_callback_handler,
    methods=["GET"],
    summary="Google OAuth Callback",
    description="Handles the OAuth callback, validates state, and returns access and refresh tokens",
    # The frontend token-exchange mode (X-Platform-Type header) authenticates users.
    # Rate limit prevents brute-forcing OAuth codes or flooding the callback.
    dependencies=[Depends(rate_limit("auth:google:callback", 10, 600))],
)
