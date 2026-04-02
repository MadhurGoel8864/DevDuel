import logging
from urllib.parse import urlencode

from fastapi import Depends, Header, Query
from fastapi.responses import RedirectResponse

from app.api.auth.schemas import GoogleCallbackResponse
from app.api.auth.services import GoogleOAuthService, get_google_oauth_auth_service
from app.core.config import settings
from app.core.security.jwt import create_access_token, create_refresh_token

logger = logging.getLogger(__name__)


async def google_login_handler(
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_auth_service),
):
    """
    Initiate Google OAuth login flow.

    Generates a secure state token and redirects the browser to Google's
    OAuth consent page.
    """
    state = await oauth_service.create_state(ttl=300)
    logger.info("Redirecting to Google OAuth login page")
    auth_url = oauth_service.get_auth_url(state)
    return RedirectResponse(url=auth_url)


async def google_callback_handler(
    code: str = Query(...),
    state: str = Query(...),
    x_platform_type: str | None = Header(default=None, alias="X-Platform-Type"),
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_auth_service),
):
    """
    Handle Google OAuth callback — two modes in one endpoint:

    Mode A — Browser redirect (called by Google):
        No X-Platform-Type header. Relays code + state to the frontend so the
        frontend can exchange them for tokens via a subsequent API call.

    Mode B — API call (called by the frontend):
        Has X-Platform-Type header. Validates and consumes the state, exchanges
        the code for tokens, and returns them as JSON.
    """
    if x_platform_type:
        # ── Mode B: frontend token-exchange call ────────────────────────────
        logger.info("OAuth callback: frontend token-exchange request")
        await oauth_service.validate_and_consume_state(state)

        user = await oauth_service.authenticate_google_user(code)

        token_payload = {
            "sub": str(user.id),
            "email": user.email,
            "provider": "google",
        }

        access_token = create_access_token(token_payload)
        refresh_token = create_refresh_token(token_payload)

        return GoogleCallbackResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    # ── Mode A: browser redirect from Google ────────────────────────────────
    logger.info("OAuth callback: browser redirect from Google, relaying to frontend")
    params = urlencode({"code": code, "state": state})
    redirect_url = f"{settings.FRONTEND_OAUTH_SUCCESS_URL}?{params}"
    return RedirectResponse(url=redirect_url)
