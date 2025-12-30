"""User API Routes"""

from fastapi import APIRouter

from app.api.users.handlers.users import create_user_handler, get_user_handler

router = APIRouter(prefix="/users", tags=["Users"])

# User URLs
router.add_api_route("", create_user_handler, methods=["POST"], status_code=201)
router.add_api_route("/{user_id}", get_user_handler, methods=["GET"])
