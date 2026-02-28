"""Teams Handler Layer"""

import logging

from fastapi import Body, Depends, Path

from app.api.auth.dependencies import get_current_user
from app.api.auth.schemas import UserWithPermissions
from app.api.teams.schemas.teams import (
    AddMemberRequest,
    SwapRolesRequest,
    TeamCreateRequest,
    TeamListResponse,
    TeamResponse,
    TeamResponseData,
    TeamSummaryData,
)
from app.api.teams.services.teams import TeamService, get_team_service

logger = logging.getLogger(__name__)


async def create_team_handler(
    request: TeamCreateRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    team_service: TeamService = Depends(get_team_service),
) -> TeamResponse:
    """Create a new team. Creator is auto-added as BIDDING member."""
    team = await team_service.create_team(
        name=request.data.name,
        creator_user_id=current_user.user_id,
    )
    logger.info(f"Team '{team.name}' created by user {current_user.user_id}")
    return TeamResponse(data=TeamResponseData.model_validate(team))


async def get_my_teams_handler(
    current_user: UserWithPermissions = Depends(get_current_user),
    team_service: TeamService = Depends(get_team_service),
) -> TeamListResponse:
    """Get all teams the authenticated user is a member of."""
    teams = await team_service.get_my_teams(user_id=current_user.user_id)
    return TeamListResponse(data=[TeamSummaryData.model_validate(t) for t in teams])


async def get_team_handler(
    team_id: str = Path(..., description="Team ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    team_service: TeamService = Depends(get_team_service),
) -> TeamResponse:
    """Get a team by ID with its members."""
    team = await team_service.get_team(team_id=team_id)
    return TeamResponse(data=TeamResponseData.model_validate(team))


async def add_member_handler(
    team_id: str = Path(..., description="Team ID"),
    request: AddMemberRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    team_service: TeamService = Depends(get_team_service),
) -> TeamResponse:
    """Add a member to a team. Only the team creator can perform this action."""
    await team_service.add_member(
        team_id=team_id,
        user_id=request.data.user_id,
        role=request.data.role,
        requesting_user_id=current_user.user_id,
    )
    # Return updated team
    team = await team_service.get_team(team_id=team_id)
    return TeamResponse(data=TeamResponseData.model_validate(team))


async def remove_member_handler(
    team_id: str = Path(..., description="Team ID"),
    user_id: str = Path(..., description="User ID to remove"),
    current_user: UserWithPermissions = Depends(get_current_user),
    team_service: TeamService = Depends(get_team_service),
) -> TeamResponse:
    """Remove a member from a team. Only the team creator can perform this action."""
    await team_service.remove_member(
        team_id=team_id,
        user_id=user_id,
        requesting_user_id=current_user.user_id,
    )
    team = await team_service.get_team(team_id=team_id)
    return TeamResponse(data=TeamResponseData.model_validate(team))


async def swap_roles_handler(
    team_id: str = Path(..., description="Team ID"),
    request: SwapRolesRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    team_service: TeamService = Depends(get_team_service),
) -> TeamResponse:
    """
    Swap roles between two team members. Only the team creator can perform this action.
    member1_id and member2_id must be TeamMember IDs (not User IDs) and must belong
    to this team. Both members must currently have different roles.
    """
    team = await team_service.swap_member_roles(
        team_id=team_id,
        member1_id=request.data.member1_id,
        member2_id=request.data.member2_id,
        requesting_user_id=current_user.user_id,
    )
    return TeamResponse(data=TeamResponseData.model_validate(team))


async def delete_team_handler(
    team_id: str = Path(..., description="Team ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    team_service: TeamService = Depends(get_team_service),
) -> TeamResponse:
    """Delete a team. Only the team creator can perform this action."""
    team = await team_service.get_team(team_id=team_id)
    response_data = TeamResponseData.model_validate(team)
    await team_service.delete_team(
        team_id=team_id,
        requesting_user_id=current_user.user_id,
    )
    logger.info(f"Team {team_id} deleted by user {current_user.user_id}")
    return TeamResponse(data=response_data)