"""Teams API Routes"""

from fastapi import APIRouter

from app.api.teams.handlers.teams import (
    add_member_handler,
    can_join_contest_handler,
    create_team_handler,
    delete_team_handler,
    get_my_role_handler,
    get_my_teams_handler,
    get_team_handler,
    get_team_status_handler,
    remove_member_handler,
    swap_roles_handler,
)

router = APIRouter(prefix="/teams", tags=["Teams"])

router.add_api_route("", create_team_handler, methods=["POST"], status_code=201)
router.add_api_route("/me", get_my_teams_handler, methods=["GET"])
router.add_api_route("/{team_id}", get_team_handler, methods=["GET"])
router.add_api_route(
    "/{team_id}/members", add_member_handler, methods=["POST"], status_code=201
)
router.add_api_route(
    "/{team_id}/members/{user_id}", remove_member_handler, methods=["DELETE"]
)
router.add_api_route(
    "/{team_id}/members/swap-roles", swap_roles_handler, methods=["POST"]
)
router.add_api_route("/{team_id}", delete_team_handler, methods=["DELETE"])
# Status / role / pre-check routes
router.add_api_route("/{team_id}/status", get_team_status_handler, methods=["GET"])
router.add_api_route("/{team_id}/my-role", get_my_role_handler, methods=["GET"])
router.add_api_route(
    "/{team_id}/can-join/{contest_id}", can_join_contest_handler, methods=["GET"]
)
