"""Auth routes module."""

from app.api.auth.routes.auth import router as AuthRouter
from app.api.auth.routes.oauth import router as OAuthRouter

__all__ = ["router"]
