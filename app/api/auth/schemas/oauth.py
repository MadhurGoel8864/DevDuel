"""
OAuth authentication schemas for Google OAuth flow.
"""

from pydantic import BaseModel


class GoogleLoginResponse(BaseModel):
    """
    Response schema for Google OAuth login initiation.

    Returns the authorization URL to redirect the user to Google's OAuth consent page.
    """

    auth_url: str

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class GoogleCallbackResponse(BaseModel):
    """
    Response schema for Google OAuth callback.

    Returns JWT access token and refresh token after successful OAuth authentication.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    class Config:
        """Pydantic configuration."""

        from_attributes = True
