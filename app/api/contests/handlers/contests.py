"""Contests Handler Layer"""

import logging

from arq.connections import ArqRedis
from fastapi import Body, Depends, Path, Query
from redis.asyncio import Redis

from app.api.auth.dependencies import get_current_user, require_organizer
from app.api.auth.schemas import UserWithPermissions
from app.api.common.dependencies import PaginationParams, get_pagination
from app.api.contests.schemas.contests import (
    ContestCreateRequest,
    ContestEditRequest,
    ContestListResponse,
    ContestPaginatedListResponse,
    ContestRegisteredTeamsResponse,
    ContestResponse,
    ContestResponseData,
    ContestSummaryData,
    DetailedLeaderboardEntryData,
    DetailedLeaderboardResponse,
    LeaderboardEntryData,
    LeaderboardResponse,
    RegisterTeamRequest,
    RegisteredTeamData,
    TeamContestDetailData,
    TeamContestDetailResponse,
    TeamContestResponseData,
    UserRegistrationCheckData,
    UserRegistrationCheckResponse,
)
from app.api.contests.services.contests import ContestService, get_contest_service
from app.core.arq_pool import get_arq_pool_dep
from app.core.enums import ContestStatus
from app.core.redis import get_redis_client
from app.core.responses import MetaResponse
from app.workers.tasks.contest_scheduler import (
    cancel_contest_end_job,
    cancel_contest_start_job,
    schedule_contest_transitions,
)

logger = logging.getLogger(__name__)


async def create_contest_handler(
    request: ContestCreateRequest = Body(...),
    current_user: UserWithPermissions = Depends(require_organizer),
    contest_service: ContestService = Depends(get_contest_service),
    arq_pool: ArqRedis = Depends(get_arq_pool_dep),
    redis: Redis = Depends(get_redis_client),
) -> ContestResponse:
    """Create a new contest. Starts in DRAFT status. Requires organizer."""
    contest = await contest_service.create_contest(
        name=request.data.name,
        description=request.data.description,
        start_time=request.data.start_time,
        end_time=request.data.end_time,
        created_by=current_user.user_id,
        starting_currency=request.data.starting_currency,
        allowed_email_domain=request.data.allowed_email_domain,
    )
    logger.info(f"Contest '{contest.name}' created by user {current_user.user_id}")
    await schedule_contest_transitions(arq_pool, redis, contest.id, contest.start_time, contest.end_time)
    return ContestResponse(data=ContestResponseData.model_validate(contest))


async def edit_contest_handler(
    contest_id: str = Path(..., description="Contest ID"),
    request: ContestEditRequest = Body(...),
    current_user: UserWithPermissions = Depends(require_organizer),
    contest_service: ContestService = Depends(get_contest_service),
    arq_pool: ArqRedis = Depends(get_arq_pool_dep),
    redis: Redis = Depends(get_redis_client),
) -> ContestResponse:
    """
    Partially update a contest (organizer/creator only).

    Allowed in any status except ENDED.
    All fields optional — only provided fields are updated.

    If any fields actually changed AND there are registered teams,
    an update email is enqueued via ARQ for each member.
    If start_time or end_time changed, existing scheduled jobs are replaced.
    """
    updated_contest, diff = await contest_service.edit_contest(
        contest_id=contest_id,
        requesting_user_id=current_user.user_id,
        name=request.data.name,
        description=request.data.description,
        start_time=request.data.start_time,
        end_time=request.data.end_time,
        starting_currency=request.data.starting_currency,
        allowed_email_domain=request.data.allowed_email_domain or None,
        clear_email_domain=request.data.allowed_email_domain == "",
    )

    if diff:
        emails = await contest_service.get_contest_member_emails(contest_id)
        for email in emails:
            await arq_pool.enqueue_job(
                "send_contest_update_task",
                email=email,
                contest_name=updated_contest.name,
                diff=diff,
            )
        if emails:
            logger.info(
                f"Contest update emails enqueued for {len(emails)} member(s) "
                f"— contest {contest_id}"
            )

        if "start_time" in diff or "end_time" in diff:
            await cancel_contest_start_job(arq_pool, redis, contest_id)
            await cancel_contest_end_job(arq_pool, redis, contest_id)
            await schedule_contest_transitions(
                arq_pool, redis, contest_id,
                updated_contest.start_time, updated_contest.end_time,
            )

    return ContestResponse(data=ContestResponseData.model_validate(updated_contest))


async def list_contests_handler(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
    pagination: PaginationParams = Depends(get_pagination),
) -> ContestListResponse:
    """List all contests (paginated)."""
    contests, total = await contest_service.list_contests(
        page=pagination.page, limit=pagination.limit
    )
    return ContestListResponse(
        data=[ContestSummaryData.model_validate(c) for c in contests],
        meta=MetaResponse(page=pagination.page, limit=pagination.limit, total=total),
    )


async def list_active_contests_handler(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
    pagination: PaginationParams = Depends(get_pagination),
) -> ContestListResponse:
    """List all ACTIVE contests (paginated)."""
    contests, total = await contest_service.list_active_contests(
        page=pagination.page, limit=pagination.limit
    )
    return ContestListResponse(
        data=[ContestSummaryData.model_validate(c) for c in contests],
        meta=MetaResponse(page=pagination.page, limit=pagination.limit, total=total),
    )


async def list_created_contests_handler(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
    pagination: PaginationParams = Depends(get_pagination),
) -> ContestListResponse:
    """List all contests created by the authenticated user (paginated)."""
    contests, total = await contest_service.list_created_contests(
        user_id=current_user.user_id, page=pagination.page, limit=pagination.limit
    )
    return ContestListResponse(
        data=[ContestSummaryData.model_validate(c) for c in contests],
        meta=MetaResponse(page=pagination.page, limit=pagination.limit, total=total),
    )


async def get_contest_handler(
    contest_id: str = Path(..., description="Contest ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
) -> ContestResponse:
    """Get a contest by ID, including registered teams with their names."""
    contest = await contest_service.get_contest(contest_id=contest_id)
    registered_teams = await contest_service.list_registered_teams(contest_id=contest_id)
    name_by_team_id = {team_id: team_name for team_id, team_name in registered_teams}

    teams_data = [
        TeamContestResponseData.model_validate(tc).model_copy(
            update={"team_name": name_by_team_id.get(tc.team_id, "")}
        )
        for tc in contest.teams
    ]
    contest_data = ContestResponseData.model_validate(contest)
    contest_data.teams = teams_data
    return ContestResponse(data=contest_data)


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
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
    pagination: PaginationParams = Depends(get_pagination),
) -> ContestListResponse:
    """Get all contests that the authenticated user's teams are participating in (paginated)."""
    contests, total = await contest_service.get_my_contests(
        user_id=current_user.user_id, page=pagination.page, limit=pagination.limit
    )
    return ContestListResponse(
        data=[ContestSummaryData.model_validate(c) for c in contests],
        meta=MetaResponse(page=pagination.page, limit=pagination.limit, total=total),
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


async def list_registered_teams_handler(
    contest_id: str = Path(..., description="Contest ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
) -> ContestRegisteredTeamsResponse:
    """List all teams registered in a contest with their id and name."""
    teams = await contest_service.list_registered_teams(contest_id=contest_id)
    data = [RegisteredTeamData(team_id=tid, team_name=name) for tid, name in teams]
    return ContestRegisteredTeamsResponse(
        data=data,
        meta=MetaResponse(total=len(data)),
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
    name_by_team_id = dict(
        await contest_service.list_registered_teams(contest_id=contest_id)
    )
    return LeaderboardResponse(
        data=[
            LeaderboardEntryData(
                rank=rank,
                team_id=tc.team_id,
                team_name=name_by_team_id.get(tc.team_id, ""),
                score=tc.score,
                currency=tc.currency,
            )
            for rank, tc in ranked
        ]
    )


async def get_detailed_leaderboard_handler(
    contest_id: str = Path(..., description="Contest ID"),
    current_user: UserWithPermissions = Depends(require_organizer),
    contest_service: ContestService = Depends(get_contest_service),
) -> DetailedLeaderboardResponse:
    """
    Organizer-only enriched leaderboard: per-team bidding efficiency and
    submission presence. Organizer must be the contest creator.
    """
    rows = await contest_service.get_detailed_leaderboard(
        contest_id=contest_id, requesting_user_id=current_user.user_id
    )
    return DetailedLeaderboardResponse(
        data=[DetailedLeaderboardEntryData(**row) for row in rows]
    )


async def check_user_registration_handler(
    contest_id: str = Path(..., description="Contest ID"),
    user_id: str = Path(..., description="User ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    contest_service: ContestService = Depends(get_contest_service),
) -> UserRegistrationCheckResponse:
    """Check whether a user is registered in a contest (via any team)."""
    is_registered = await contest_service.is_user_registered(
        contest_id=contest_id, user_id=user_id
    )
    return UserRegistrationCheckResponse(
        data=UserRegistrationCheckData(
            contest_id=contest_id,
            user_id=user_id,
            is_registered=is_registered,
        )
    )


# ── Admin Lifecycle Endpoints ──────────────────────────────────────────────────


async def open_registration_handler(
    contest_id: str = Path(..., description="Contest ID"),
    current_user: UserWithPermissions = Depends(require_organizer),
    contest_service: ContestService = Depends(get_contest_service),
) -> ContestResponse:
    """Open registration for a contest (DRAFT → REGISTRATION_OPEN).
    Only the contest creator (organizer) may call this.
    """
    contest = await contest_service.update_contest_status(
        contest_id=contest_id,
        new_status=ContestStatus.REGISTRATION_OPEN,
        requesting_user_id=current_user.user_id,
    )
    return ContestResponse(data=ContestResponseData.model_validate(contest))


async def start_contest_handler(
    contest_id: str = Path(..., description="Contest ID"),
    current_user: UserWithPermissions = Depends(require_organizer),
    contest_service: ContestService = Depends(get_contest_service),
    arq_pool: ArqRedis = Depends(get_arq_pool_dep),
    redis: Redis = Depends(get_redis_client),
) -> ContestResponse:
    """Start a contest (REGISTRATION_OPEN → ACTIVE).
    Only the contest creator (organizer) may call this.
    Cancels the scheduled auto-start job so it doesn't double-fire.
    """
    contest = await contest_service.update_contest_status(
        contest_id=contest_id,
        new_status=ContestStatus.ACTIVE,
        requesting_user_id=current_user.user_id,
    )
    await cancel_contest_start_job(arq_pool, redis, contest_id)
    return ContestResponse(data=ContestResponseData.model_validate(contest))


async def end_contest_handler(
    contest_id: str = Path(..., description="Contest ID"),
    current_user: UserWithPermissions = Depends(require_organizer),
    contest_service: ContestService = Depends(get_contest_service),
    arq_pool: ArqRedis = Depends(get_arq_pool_dep),
    redis: Redis = Depends(get_redis_client),
) -> ContestResponse:
    """End a contest (ACTIVE → ENDED).
    Only the contest creator (organizer) may call this.
    Cancels the scheduled auto-end job so it doesn't double-fire.
    """
    contest = await contest_service.update_contest_status(
        contest_id=contest_id,
        new_status=ContestStatus.ENDED,
        requesting_user_id=current_user.user_id,
    )
    await cancel_contest_end_job(arq_pool, redis, contest_id)
    return ContestResponse(data=ContestResponseData.model_validate(contest))
