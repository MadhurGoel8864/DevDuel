"""User API Routes"""

from fastapi import APIRouter, Depends

from app.api.users.handlers.users import (
    create_user_handler,
    get_user_handler,
    get_users_handler,
    update_profile_handler,
)
from app.core.rate_limit import rate_limit

router = APIRouter(prefix="/users", tags=["Users"])

# User URLs
router.add_api_route(
    "",
    create_user_handler,
    methods=["POST"],
    status_code=201,
    # Unauthenticated endpoint that creates accounts and sends OTP emails.
    # Matches /auth/register limits to prevent this from being used as a bypass.
    dependencies=[Depends(rate_limit("users:create", 3, 3600))],
)
router.add_api_route("/me", update_profile_handler, methods=["PATCH"])
router.add_api_route("/{user_id}", get_user_handler, methods=["GET"])
router.add_api_route("", get_users_handler, methods=["GET"])  # TODO: Remove
