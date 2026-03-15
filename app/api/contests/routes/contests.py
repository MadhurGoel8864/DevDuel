"""Contests API Routes"""

from fastapi import APIRouter

from app.api.contests.handlers.contests import (
    create_contest_handler,
    edit_contest_handler,
    end_contest_handler,
    get_contest_handler,
    get_contest_leaderboard_handler,
    get_my_contests_handler,
    get_team_in_contest_handler,
    list_active_contests_handler,
    list_contests_handler,
    open_registration_handler,
    register_team_handler,
    start_contest_handler,
)

router = APIRouter(prefix="/contests", tags=["Contests"])

# Static paths must be declared before parameterized paths to avoid conflicts
router.add_api_route("", create_contest_handler, methods=["POST"], status_code=201)
router.add_api_route("", list_contests_handler, methods=["GET"])
router.add_api_route("/active", list_active_contests_handler, methods=["GET"])
router.add_api_route("/me", get_my_contests_handler, methods=["GET"])
router.add_api_route("/{contest_id}", get_contest_handler, methods=["GET"])

# Edit contest — PATCH (partial update, creator only, not allowed when ENDED)
router.add_api_route(
    "/{contest_id}",
    edit_contest_handler,
    methods=["PATCH"],
    summary="Edit Contest",
    description=(
        "Partially update a contest. All fields optional. "
        "Sends update email to all registered team members if anything changed. "
        "Not allowed when contest status is ENDED."
    ),
)

router.add_api_route(
    "/{contest_id}/register", register_team_handler, methods=["POST"], status_code=201
)
# Leaderboard and team-in-contest
router.add_api_route(
    "/{contest_id}/teams", get_contest_leaderboard_handler, methods=["GET"]
)
router.add_api_route(
    "/{contest_id}/teams/{team_id}", get_team_in_contest_handler, methods=["GET"]
)
# Admin lifecycle transitions
router.add_api_route(
    "/{contest_id}/open-registration",
    open_registration_handler,
    methods=["POST"],
)
router.add_api_route(
    "/{contest_id}/start",
    start_contest_handler,
    methods=["POST"],
)
router.add_api_route(
    "/{contest_id}/end",
    end_contest_handler,
    methods=["POST"],
)
