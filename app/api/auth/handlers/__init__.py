"""Auth handlers module."""

from app.api.auth.handlers.auth import (
    get_profile_handler,
    protected_route_handler,
    login_handler,
)

__all__ = ["get_profile_handler", "protected_route_handler"]
