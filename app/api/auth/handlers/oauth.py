import logging

from fastapi import Depends, Query
from fastapi.responses import RedirectResponse

from app.api.auth.schemas import GoogleCallbackResponse
from app.api.auth.services import GoogleOAuthService, get_google_oauth_auth_service
from app.core.security.jwt import create_access_token, create_refresh_token

logger = logging.getLogger(__name__)


async def google_login_handler(
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_auth_service),
):
    """
    Initiate Google OAuth login flow.

    Generates a secure state token and returns the Google OAuth authorization URL.

    Args:
        oauth_service: Injected GoogleOAuthService instance.

    Returns:
        GoogleLoginResponse: Contains the authorization URL.
    """
    state = await oauth_service.create_state(ttl=300)
    logger.info("Redirecting to Google OAuth login page")
    auth_url = oauth_service.get_auth_url(state)
    return RedirectResponse(url=auth_url)
    # return GoogleLoginResponse(auth_url=auth_url) # TODO: Use it when connected to FrontEnd


async def google_callback_handler(
    code: str = Query(...),
    state: str = Query(...),
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_auth_service),
) -> GoogleCallbackResponse:
    """
    Handle Google OAuth callback.

    Validates the OAuth state, exchanges the authorization code for user info,
    and returns JWT access and refresh tokens.

    Args:
        code: Authorization code from Google.
        state: State token for CSRF protection.
        oauth_service: Injected GoogleOAuthService instance.

    Returns:
        GoogleCallbackResponse: Contains access_token, refresh_token, and token_type.
    """
    await oauth_service.validate_and_consume_state(state)

    user = await oauth_service.authenticate_google_user(code)

    # Create token payload
    token_payload = {
        "sub": str(user.id),
        "email": user.email,
        "provider": "google",
    }

    # Generate both access and refresh tokens
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)

    return GoogleCallbackResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )
