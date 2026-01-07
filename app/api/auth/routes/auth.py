"""Authentication API Routes"""

from fastapi import APIRouter

from app.api.auth.handlers import (
    get_profile_handler,
    protected_route_handler,
    login_handler,
    refresh_token_handler,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Authentication URLs
router.add_api_route("/login", login_handler, methods=["POST"])
router.add_api_route("/refresh", refresh_token_handler, methods=["POST"])
router.add_api_route("/me", get_profile_handler, methods=["GET"])
router.add_api_route("/protected", protected_route_handler, methods=["GET"])
