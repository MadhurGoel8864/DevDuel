"""Team Join Request Handlers"""

import logging

from arq.connections import ArqRedis
from fastapi import Body, Depends, Path

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
from app.core.arq_pool import get_arq_pool_dep
from app.core.responses import MetaResponse

logger = logging.getLogger(__name__)


async def browse_teams_handler(
    pagination: PaginationParams = Depends(get_pagination),
    current_user: UserWithPermissions = Depends(get_current_user),
    service: TeamJoinRequestService = Depends(get_team_join_request_service),
) -> BrowseTeamsResponse:
    """Paginated list of teams the user is not yet in."""
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
    current_user: UserWithPermissions = Depends(get_current_user),
    service: TeamJoinRequestService = Depends(get_team_join_request_service),
    arq_pool: ArqRedis = Depends(get_arq_pool_dep),
) -> MessageResponse:
    """Send a join request to a team. Auto-assigns role; emails the leader."""
    result = await service.send_request(
        user_id=current_user.user_id,
        team_id=request.data.team_id,
    )

    if result.get("leader_email"):
        await arq_pool.enqueue_job(
            "send_join_request_leader_task",
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
    current_user: UserWithPermissions = Depends(get_current_user),
    service: TeamJoinRequestService = Depends(get_team_join_request_service),
    arq_pool: ArqRedis = Depends(get_arq_pool_dep),
) -> MessageResponse:
    """Leader accepts a pending request; requester is added and emailed."""
    result = await service.accept(
        team_id=team_id,
        request_id=request_id,
        requesting_user_id=current_user.user_id,
    )

    if result.get("requester_email"):
        await arq_pool.enqueue_job(
            "send_join_request_accepted_task",
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
