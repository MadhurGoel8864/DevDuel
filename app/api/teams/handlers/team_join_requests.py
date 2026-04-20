"""Team Join Request Handlers"""

import logging

from fastapi import BackgroundTasks, Body, Depends, Path

from app.api.auth.dependencies import get_current_user
from app.api.auth.schemas import UserWithPermissions
from app.api.common.dependencies import PaginationParams, get_pagination
from app.api.common.responses import MessageResponse
from app.api.teams.schemas.team_join_requests import (
    BrowseTeamItemData,
    BrowseTeamsResponse,
    JoinRequestCreateRequest,
    JoinRequestListResponse,
    JoinRequestResponse,
    JoinRequestResponseData,
)
from app.api.teams.services.team_join_requests import (
    TeamJoinRequestService,
    get_team_join_request_service,
)
from app.core.responses import MetaResponse
from app.services.email import email_service
from app.services.email.templates.team_join_request import (
    team_join_request_accepted_template,
    team_join_request_leader_template,
)

logger = logging.getLogger(__name__)


# ── Background email tasks ─────────────────────────────────────────────────────


def _send_leader_notification(
    leader_email: str,
    leader_name: str | None,
    team_name: str,
    requester_name: str | None,
    requester_email: str,
    role: str,
    manage_url: str,
) -> None:
    try:
        subject, html_body = team_join_request_leader_template(
            leader_name=leader_name,
            team_name=team_name,
            requester_name=requester_name,
            requester_email=requester_email,
            role=role,
            manage_url=manage_url,
        )
        email_service.send_email(
            to_email=leader_email, subject=subject, body=html_body, html=True
        )
        logger.info(f"Join request leader notification sent to {leader_email}")
    except Exception as e:
        logger.error(
            f"Failed to send join request leader notification to {leader_email}: {e}"
        )


def _send_acceptance_notification(
    requester_email: str,
    requester_name: str | None,
    team_name: str,
    role: str,
    team_url: str,
) -> None:
    try:
        subject, html_body = team_join_request_accepted_template(
            requester_name=requester_name,
            team_name=team_name,
            role=role,
            team_url=team_url,
        )
        email_service.send_email(
            to_email=requester_email, subject=subject, body=html_body, html=True
        )
        logger.info(f"Join request acceptance email sent to {requester_email}")
    except Exception as e:
        logger.error(
            f"Failed to send join request acceptance email to {requester_email}: {e}"
        )


# ── Handlers ───────────────────────────────────────────────────────────────────


async def browse_teams_handler(
    pagination: PaginationParams = Depends(get_pagination),
    current_user: UserWithPermissions = Depends(get_current_user),
    service: TeamJoinRequestService = Depends(get_team_join_request_service),
) -> BrowseTeamsResponse:
    """Paginated list of teams the user is not yet in. Each item includes
    member_count, is_open, and open_roles so the frontend can disable the
    request button on full teams."""
    items, total = await service.browse_teams(
        user_id=current_user.user_id,
        limit=pagination.limit,
        offset=pagination.skip,
    )
    return BrowseTeamsResponse(
        data=[BrowseTeamItemData.model_validate(i) for i in items],
        meta=MetaResponse(
            page=pagination.page, limit=pagination.limit, total=total
        ),
    )


async def send_join_request_handler(
    request: JoinRequestCreateRequest = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: UserWithPermissions = Depends(get_current_user),
    service: TeamJoinRequestService = Depends(get_team_join_request_service),
) -> MessageResponse:
    """Send a join request to a team. Auto-assigns role; emails the leader."""
    result = await service.send_request(
        user_id=current_user.user_id,
        team_id=request.data.team_id,
    )

    if result.get("leader_email"):
        background_tasks.add_task(
            _send_leader_notification,
            leader_email=result["leader_email"],
            leader_name=result.get("leader_name"),
            team_name=result["team_name"],
            requester_name=result.get("requester_name"),
            requester_email=result.get("requester_email") or "",
            role=result["role"],
            manage_url=result["manage_url"],
        )

    return MessageResponse(
        message=f"Join request sent for team '{result['team_name']}'."
    )


async def list_team_join_requests_handler(
    team_id: str = Path(..., description="Team ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    service: TeamJoinRequestService = Depends(get_team_join_request_service),
) -> JoinRequestListResponse:
    """Leader-only: list pending join requests for the given team."""
    items = await service.list_for_team(
        team_id=team_id, requesting_user_id=current_user.user_id
    )
    return JoinRequestListResponse(
        data=[JoinRequestResponseData.model_validate(i) for i in items]
    )


async def list_my_join_requests_handler(
    current_user: UserWithPermissions = Depends(get_current_user),
    service: TeamJoinRequestService = Depends(get_team_join_request_service),
) -> JoinRequestListResponse:
    """Requester's own join request history (all statuses)."""
    items = await service.list_for_user(user_id=current_user.user_id)
    return JoinRequestListResponse(
        data=[JoinRequestResponseData.model_validate(i) for i in items]
    )


async def accept_join_request_handler(
    team_id: str = Path(..., description="Team ID"),
    request_id: str = Path(..., description="Join request ID"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: UserWithPermissions = Depends(get_current_user),
    service: TeamJoinRequestService = Depends(get_team_join_request_service),
) -> MessageResponse:
    """Leader accepts a pending request; requester is added and emailed."""
    result = await service.accept(
        team_id=team_id,
        request_id=request_id,
        requesting_user_id=current_user.user_id,
    )

    if result.get("requester_email"):
        background_tasks.add_task(
            _send_acceptance_notification,
            requester_email=result["requester_email"],
            requester_name=result.get("requester_name"),
            team_name=result["team_name"],
            role=result["role"],
            team_url=result["team_url"],
        )

    return MessageResponse(message="Join request accepted. Member added to the team.")


async def reject_join_request_handler(
    team_id: str = Path(..., description="Team ID"),
    request_id: str = Path(..., description="Join request ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    service: TeamJoinRequestService = Depends(get_team_join_request_service),
) -> MessageResponse:
    """Leader rejects a pending request. No email sent to requester."""
    await service.reject(
        team_id=team_id,
        request_id=request_id,
        requesting_user_id=current_user.user_id,
    )
    return MessageResponse(message="Join request rejected.")


async def cancel_join_request_handler(
    request_id: str = Path(..., description="Join request ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    service: TeamJoinRequestService = Depends(get_team_join_request_service),
) -> MessageResponse:
    """Cancel a pending request — allowed for the requester or the team leader."""
    await service.cancel(
        request_id=request_id, requesting_user_id=current_user.user_id
    )
    return MessageResponse(message="Join request cancelled.")
