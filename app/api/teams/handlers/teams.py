"""Teams Handler Layer"""

import logging

from fastapi import Body, Depends, Path

from app.api.auth.dependencies import get_current_user
from app.api.auth.schemas import UserWithPermissions
from app.api.contests.services.contests import ContestService, get_contest_service
from app.api.teams.schemas.teams import (
    AddMemberRequest,
    CanJoinResponse,
    CanJoinResponseData,
    TeamCreateRequest,
    TeamListResponse,
    TeamResponse,
    TeamResponseData,
    TeamRoleResponse,
    TeamRoleResponseData,
    TeamStatusResponse,
    TeamStatusResponseData,
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


async def get_team_status_handler(
    team_id: str = Path(..., description="Team ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    team_service: TeamService = Depends(get_team_service),
) -> TeamStatusResponse:
    """
    Return whether a team is contest-ready (has both BIDDING and CODING filled).
    """
    status = await team_service.get_team_status(team_id=team_id)
    return TeamStatusResponse(
        data=TeamStatusResponseData(
            is_ready=status.is_ready,
            has_bidder=status.has_bidder,
            has_coder=status.has_coder,
            member_count=status.member_count,
            missing_roles=status.missing_roles,
        )
    )


async def get_my_role_handler(
    team_id: str = Path(..., description="Team ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    team_service: TeamService = Depends(get_team_service),
) -> TeamRoleResponse:
    """
    Return the authenticated user's role in the given team.
    Used by the frontend to render role-specific UI.
    """
    role = await team_service.get_user_role_in_team(
        team_id=team_id, user_id=current_user.user_id
    )
    return TeamRoleResponse(
        data=TeamRoleResponseData(
            team_id=team_id,
            user_id=current_user.user_id,
            role=role,
            is_member=role is not None,
        )
    )


async def can_join_contest_handler(
    team_id: str = Path(..., description="Team ID"),
    contest_id: str = Path(..., description="Contest ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    team_service: TeamService = Depends(get_team_service),
    contest_service: ContestService = Depends(get_contest_service),
) -> CanJoinResponse:
    """
    Pre-check whether this team can join the given contest.
    Internally calls get_team_status() — no readiness logic duplicated here.
    """
    # Fetch contest state needed by team_service.can_join_contest
    contest = await contest_service.get_contest(contest_id=contest_id)
    existing = await contest_service.get_team_in_contest_safe(
        contest_id=contest_id, team_id=team_id
    )

    can_join, reasons = await team_service.can_join_contest(
        team_id=team_id,
        contest_status=contest.status,
        already_registered=existing is not None,
    )
    return CanJoinResponse(
        data=CanJoinResponseData(
            team_id=team_id,
            contest_id=contest_id,
            can_join=can_join,
            reasons=reasons,
        )
    )
