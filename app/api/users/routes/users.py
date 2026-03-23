"""User API Routes"""

from fastapi import APIRouter

from app.api.users.handlers.users import (
    create_user_handler,
    get_user_handler,
    get_users_handler,
    update_profile_handler,
)

router = APIRouter(prefix="/users", tags=["Users"])

# User URLs
router.add_api_route("", create_user_handler, methods=["POST"], status_code=201)
router.add_api_route("/me", update_profile_handler, methods=["PATCH"])
router.add_api_route("/{user_id}", get_user_handler, methods=["GET"])
router.add_api_route("", get_users_handler, methods=["GET"])  # TODO: Remove
