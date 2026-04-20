"""Teams API Routes"""

from fastapi import APIRouter

from app.api.common.responses import MessageResponse
from app.api.teams.handlers.team_invites import (
    accept_invite_handler,
    decline_invite_handler,
    send_invite_handler,
    validate_invite_handler,
)
from app.api.teams.handlers.team_join_requests import (
    accept_join_request_handler,
    browse_teams_handler,
    cancel_join_request_handler,
    list_my_join_requests_handler,
    list_team_join_requests_handler,
    reject_join_request_handler,
    send_join_request_handler,
)
from app.api.teams.handlers.teams import (
    add_member_handler,
    can_join_contest_handler,
    create_team_handler,
    delete_team_handler,
    get_my_role_handler,
    get_my_teams_handler,
    get_team_handler,
    get_team_status_handler,
    leave_team_handler,
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

# No request body — auto-fetches both members and swaps
router.add_api_route(
    "/{team_id}/members/swap-roles",
    swap_roles_handler,
    methods=["POST"],
    summary="Swap member roles",
    description=(
        "Swap the roles of the two team members. Creator only. "
        "No request body needed — team has exactly 2 members."
    ),
)

# ── Team Invites ───────────────────────────────────────────────────────────────
# NOTE: /invite/* must be declared BEFORE /{team_id} to avoid routing conflicts
router.add_api_route(
    "/invite/validate",
    validate_invite_handler,
    methods=["GET"],
    summary="Validate Invite Token",
    description="No auth required. Called by frontend when invite link is opened.",
)
router.add_api_route(
    "/invite/accept",
    accept_invite_handler,
    methods=["POST"],
    summary="Accept Team Invite",
)
router.add_api_route(
    "/invite/decline",
    decline_invite_handler,
    methods=["POST"],
    summary="Decline Team Invite",
)
router.add_api_route(
    "/{team_id}/invite",
    send_invite_handler,
    methods=["POST"],
    status_code=201,
    summary="Send Team Invite",
    description="Send invite to email. Works for registered and new users.",
)

# ── Join Requests ──────────────────────────────────────────────────────────────
# NOTE: /join-requests/* must be declared BEFORE /{team_id} to avoid path capture
router.add_api_route(
    "/join-requests/browse",
    browse_teams_handler,
    methods=["GET"],
    summary="Browse Teams to Join",
    description="Paginated list of teams the user is not in. Includes open-slot info.",
)
router.add_api_route(
    "/join-requests/me",
    list_my_join_requests_handler,
    methods=["GET"],
    summary="My Join Request History",
)
router.add_api_route(
    "/join-requests",
    send_join_request_handler,
    methods=["POST"],
    status_code=201,
    summary="Send Join Request",
    description="Auto-assigns role to whichever slot is open in the target team.",
)
router.add_api_route(
    "/join-requests/{request_id}/cancel",
    cancel_join_request_handler,
    methods=["POST"],
    summary="Cancel Join Request",
    description="Cancellable by the requester or the team leader.",
)

# ── Status / role / pre-check ──────────────────────────────────────────────────
router.add_api_route("/{team_id}/status", get_team_status_handler, methods=["GET"])
router.add_api_route("/{team_id}/my-role", get_my_role_handler, methods=["GET"])
router.add_api_route(
    "/{team_id}/can-join/{contest_id}", can_join_contest_handler, methods=["GET"]
)

# ── Leave team ─────────────────────────────────────────────────────────────────
router.add_api_route(
    "/{team_id}/leave",
    leave_team_handler,
    methods=["DELETE"],
    response_model=MessageResponse,
    summary="Leave a team",
    description=(
        "Member voluntarily leaves a team. "
        "Creator must delete the team instead. "
        "If team is in an open/active contest, it is marked inactive."
    ),
)

# ── Team-scoped Join Request actions ───────────────────────────────────────────
router.add_api_route(
    "/{team_id}/join-requests",
    list_team_join_requests_handler,
    methods=["GET"],
    summary="List Pending Join Requests",
    description="Team creator only.",
)
router.add_api_route(
    "/{team_id}/join-requests/{request_id}/accept",
    accept_join_request_handler,
    methods=["POST"],
    summary="Accept Join Request",
    description="Team creator only. Adds the requester as a member and emails them.",
)
router.add_api_route(
    "/{team_id}/join-requests/{request_id}/reject",
    reject_join_request_handler,
    methods=["POST"],
    summary="Reject Join Request",
    description="Team creator only. No email is sent to the requester.",
)

router.add_api_route(
    "/{team_id}",
    delete_team_handler,
    methods=["DELETE"],
    summary="Delete a team",
    description=(
        "Permanently delete a team. Creator only. "
        "Not allowed if team is in an active contest."
    ),
)
