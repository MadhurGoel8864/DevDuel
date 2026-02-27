"""Contests API Routes"""

from fastapi import APIRouter

from app.api.contests.handlers.contests import (
    create_contest_handler,
    get_contest_handler,
    get_my_contests_handler,
    list_active_contests_handler,
    list_contests_handler,
    register_team_handler,
)

router = APIRouter(prefix="/contests", tags=["Contests"])

# Static paths must be declared before parameterized paths to avoid conflicts
router.add_api_route("", create_contest_handler, methods=["POST"], status_code=201)
router.add_api_route("", list_contests_handler, methods=["GET"])
router.add_api_route("/active", list_active_contests_handler, methods=["GET"])
router.add_api_route("/me", get_my_contests_handler, methods=["GET"])
router.add_api_route("/{contest_id}", get_contest_handler, methods=["GET"])
router.add_api_route(
    "/{contest_id}/register", register_team_handler, methods=["POST"], status_code=201
)
