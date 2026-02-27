"""Contests Handler Layer"""

import logging

from fastapi import Body, Depends, Path

from app.api.auth.dependencies import get_current_user
from app.api.auth.schemas import UserWithPermissions
from app.api.contests.schemas.contests import (
    ContestCreateRequest,
    ContestListResponse,
    ContestResponse,
    ContestResponseData,
    ContestSummaryData,
    RegisterTeamRequest,
)
from app.api.contests.services.contests import ContestService, get_contest_service

logger = logging.getLogger(__name__)


async def create_contest_handler(
    request: ContestCreateRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
) -> ContestResponse:
    """Create a new contest."""
    contest = await contest_service.create_contest(
        name=request.data.name,
        description=request.data.description,
        start_time=request.data.start_time,
        end_time=request.data.end_time,
    )
    logger.info(f"Contest '{contest.name}' created by user {current_user.user_id}")
    return ContestResponse(data=ContestResponseData.model_validate(contest))


async def list_contests_handler(
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
) -> ContestListResponse:
    """List all contests."""
    contests = await contest_service.list_contests()
    return ContestListResponse(
        data=[ContestSummaryData.model_validate(c) for c in contests]
    )


async def list_active_contests_handler(
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
) -> ContestListResponse:
    """List all active contests."""
    contests = await contest_service.list_active_contests()
    return ContestListResponse(
        data=[ContestSummaryData.model_validate(c) for c in contests]
    )


async def get_contest_handler(
    contest_id: str = Path(..., description="Contest ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
) -> ContestResponse:
    """Get a contest by ID, including registered teams."""
    contest = await contest_service.get_contest(contest_id=contest_id)
    return ContestResponse(data=ContestResponseData.model_validate(contest))


async def register_team_handler(
    contest_id: str = Path(..., description="Contest ID"),
    request: RegisterTeamRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
) -> ContestResponse:
    """Register a team for a contest. Only the team creator can register."""
    await contest_service.register_team(
        contest_id=contest_id,
        team_id=request.data.team_id,
        requesting_user_id=current_user.user_id,
    )
    contest = await contest_service.get_contest(contest_id=contest_id)
    return ContestResponse(data=ContestResponseData.model_validate(contest))


async def get_my_contests_handler(
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
) -> ContestListResponse:
    """Get all contests that the authenticated user's teams are participating in."""
    contests = await contest_service.get_my_contests(user_id=current_user.user_id)
    return ContestListResponse(
        data=[ContestSummaryData.model_validate(c) for c in contests]
    )
