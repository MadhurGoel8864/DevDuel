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
    LeaderboardEntryData,
    LeaderboardResponse,
    RegisterTeamRequest,
    TeamContestDetailData,
    TeamContestDetailResponse,
)
from app.api.contests.services.contests import ContestService, get_contest_service
from app.core.enums import ContestStatus

logger = logging.getLogger(__name__)


async def create_contest_handler(
    request: ContestCreateRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
) -> ContestResponse:
    """Create a new contest. Starts in DRAFT status."""
    contest = await contest_service.create_contest(
        name=request.data.name,
        description=request.data.description,
        start_time=request.data.start_time,
        end_time=request.data.end_time,
        created_by=current_user.user_id,
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
    """List all ACTIVE contests."""
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
    """Register a team for a contest. Only the team creator can register.
    Contest must be in REGISTRATION_OPEN status.
    """
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


async def get_team_in_contest_handler(
    contest_id: str = Path(..., description="Contest ID"),
    team_id: str = Path(..., description="Team ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
) -> TeamContestDetailResponse:
    """
    Return the TeamContest state (currency, score) for a specific team in a contest.
    Used by the team dashboard.
    """
    registration = await contest_service.get_team_in_contest(
        contest_id=contest_id, team_id=team_id
    )
    return TeamContestDetailResponse(
        data=TeamContestDetailData.model_validate(registration)
    )


async def get_contest_leaderboard_handler(
    contest_id: str = Path(..., description="Contest ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
) -> LeaderboardResponse:
    """
    Return all teams in a contest ranked by score desc, then currency desc.
    """
    ranked = await contest_service.get_contest_leaderboard(contest_id=contest_id)
    return LeaderboardResponse(
        data=[
            LeaderboardEntryData(
                rank=rank,
                team_id=tc.team_id,
                score=tc.score,
                currency=tc.currency,
            )
            for rank, tc in ranked
        ]
    )


# ── Admin Lifecycle Endpoints ──────────────────────────────────────────────────


async def open_registration_handler(
    contest_id: str = Path(..., description="Contest ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
) -> ContestResponse:
    """Open registration for a contest (DRAFT → REGISTRATION_OPEN).
    Only the contest creator may call this.
    """
    contest = await contest_service.update_contest_status(
        contest_id=contest_id,
        new_status=ContestStatus.REGISTRATION_OPEN,
        requesting_user_id=current_user.user_id,
    )
    return ContestResponse(data=ContestResponseData.model_validate(contest))


async def start_contest_handler(
    contest_id: str = Path(..., description="Contest ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
) -> ContestResponse:
    """Start a contest (REGISTRATION_OPEN → ACTIVE).
    Only the contest creator may call this.
    """
    contest = await contest_service.update_contest_status(
        contest_id=contest_id,
        new_status=ContestStatus.ACTIVE,
        requesting_user_id=current_user.user_id,
    )
    return ContestResponse(data=ContestResponseData.model_validate(contest))


async def end_contest_handler(
    contest_id: str = Path(..., description="Contest ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
) -> ContestResponse:
    """End a contest (ACTIVE → ENDED).
    Only the contest creator may call this.
    """
    contest = await contest_service.update_contest_status(
        contest_id=contest_id,
        new_status=ContestStatus.ENDED,
        requesting_user_id=current_user.user_id,
    )
    return ContestResponse(data=ContestResponseData.model_validate(contest))
