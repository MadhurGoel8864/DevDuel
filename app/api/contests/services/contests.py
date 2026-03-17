"""Contest Service Layer"""

import logging
from datetime import datetime

from fastapi import Depends

from app.api.contests.dao.contests import (
    ContestDAO,
    TeamContestDAO,
    get_contest_dao,
    get_team_contest_dao,
)
from app.api.teams.services.teams import TeamService, get_team_service
from app.core.enums import ContestStatus
from app.core.exceptions.contests import (
    ContestAlreadyRegisteredException,
    ContestNotFoundException,
    InvalidContestStateTransition,
    RegistrationClosedException,
)
from app.core.exceptions.teams import NotTeamCreatorException
from app.database.models.contests import Contest, TeamContest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid one-step transitions for the contest lifecycle state machine
# ---------------------------------------------------------------------------
_VALID_TRANSITIONS: dict[ContestStatus, ContestStatus] = {
    ContestStatus.DRAFT: ContestStatus.REGISTRATION_OPEN,
    ContestStatus.REGISTRATION_OPEN: ContestStatus.ACTIVE,
    ContestStatus.ACTIVE: ContestStatus.ENDED,
}


def ensure_contest_status(
    contest: Contest, allowed_statuses: list[ContestStatus]
) -> None:
    """Raise RegistrationClosedException if contest.status is not in allowed_statuses.

    Reusable helper — call this before any operation that requires the contest
    to be in a specific lifecycle stage.
    """
    if contest.status not in allowed_statuses:
        raise RegistrationClosedException(contest_id=contest.id)


class ContestService:
    """Business logic for Contest operations."""

    def __init__(
        self,
        contest_dao: ContestDAO,
        team_contest_dao: TeamContestDAO,
        team_service: TeamService,
    ):
        self._contest_dao = contest_dao
        self._team_contest_dao = team_contest_dao
        self._team_service = team_service

    async def create_contest(
        self,
        name: str,
        start_time: datetime,
        end_time: datetime,
        created_by: str,
        description: str | None = None,
    ) -> Contest:
        """
        Create a new contest. Starts in DRAFT status.

        Args:
            name: Contest name.
            start_time: Contest start datetime.
            end_time: Contest end datetime.
            created_by: User ID of the creator (used for admin checks).
            description: Optional description.

        Returns:
            Created Contest instance.
        """
        logger.info(f"Creating contest '{name}' by user {created_by}")
        contest = await self._contest_dao.create(
            name=name,
            description=description,
            start_time=start_time,
            end_time=end_time,
            created_by=created_by,
        )
        logger.info(f"Contest '{name}' created with id {contest.id}")
        return contest

    async def get_contest(self, contest_id: str) -> Contest:
        """
        Get a contest by ID.

        Raises:
            ContestNotFoundException: If contest does not exist.
        """
        contest = await self._contest_dao.get_by_id(contest_id)
        if not contest:
            raise ContestNotFoundException(contest_id=contest_id)
        return contest

    async def list_contests(self) -> list[Contest]:
        """Return all contests."""
        return await self._contest_dao.get_all()

    async def list_active_contests(self) -> list[Contest]:
        """Return only contests with ACTIVE status."""
        return await self._contest_dao.get_active()

    async def list_created_contests(self, user_id: str) -> list[Contest]:
        """Return all contests created by the given user."""
        return await self._contest_dao.get_created_by(user_id)

    # ------------------------------------------------------------------
    # Lifecycle State Machine
    # ------------------------------------------------------------------

    async def update_contest_status(
        self,
        contest_id: str,
        new_status: ContestStatus,
        requesting_user_id: str,
    ) -> Contest:
        """
        Transition a contest to a new lifecycle status.

        Valid transitions:
            DRAFT → REGISTRATION_OPEN
            REGISTRATION_OPEN → ACTIVE
            ACTIVE → ENDED

        Only the contest creator (admin) may call this.

        Raises:
            ContestNotFoundException: If contest does not exist.
            NotTeamCreatorException: If requester is not the contest creator.
            InvalidContestStateTransition: If the transition is not allowed.
        """
        contest = await self.get_contest(contest_id)

        # Admin check — only the contest creator may drive the lifecycle
        if contest.created_by != requesting_user_id:
            raise NotTeamCreatorException(
                message="Only the contest creator can change the contest status"
            )

        # Validate the transition
        expected_next = _VALID_TRANSITIONS.get(contest.status)
        if expected_next != new_status:
            raise InvalidContestStateTransition(
                from_status=contest.status.value,
                to_status=new_status.value,
            )

        updated = await self._contest_dao.update_status(contest, new_status)
        logger.info(
            f"Contest {contest_id} transitioned: {contest.status.value} → {new_status.value}"
        )
        return updated

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    async def register_team(
        self,
        contest_id: str,
        team_id: str,
        requesting_user_id: str,
    ) -> TeamContest:
        """
        Register a team for a contest. Only the team creator can register.

        Raises:
            ContestNotFoundException: If contest does not exist.
            RegistrationClosedException: If contest status ≠ REGISTRATION_OPEN.
            NotTeamCreatorException: If requester is not the team creator.
            ContestAlreadyRegisteredException: If team is already registered.
        """
        contest = await self.get_contest(contest_id)

        # Enforce lifecycle — only allowed during REGISTRATION_OPEN
        ensure_contest_status(contest, [ContestStatus.REGISTRATION_OPEN])

        # Validate team exists and requesting user is its creator
        team = await self._team_service.get_team(team_id=team_id)
        if team.created_by != requesting_user_id:
            raise NotTeamCreatorException(
                message="Only the team creator can register the team for a contest"
            )

        # Validate team readiness (2 members, both roles filled)
        team_status = await self._team_service.get_team_status(team_id=team_id)
        if not team_status.is_ready:
            from app.core.exceptions.common import BadRequestException

            raise BadRequestException(
                message=(
                    f"Team is not contest-ready. "
                    f"Missing roles: {', '.join(team_status.missing_roles)}"
                )
            )

        existing = await self._team_contest_dao.get(
            team_id=team_id, contest_id=contest_id
        )
        if existing:
            raise ContestAlreadyRegisteredException(
                team_id=team_id, contest_id=contest_id
            )

        registration = await self._team_contest_dao.register(
            team_id=team_id, contest_id=contest_id
        )
        logger.info(f"Team {team_id} registered for contest {contest_id}")
        return registration

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_my_contests(self, user_id: str) -> list[Contest]:
        """
        Get all contests that any of the user's teams are participating in.
        """
        team_ids = await self._team_service.get_my_teams(user_id)
        contest_ids: set[str] = set()

        for team in team_ids:
            registrations = await self._team_contest_dao.get_by_team(team.id)
            for reg in registrations:
                contest_ids.add(reg.contest_id)

        contests = []
        for contest_id in contest_ids:
            contest = await self._contest_dao.get_by_id(contest_id)
            if contest:
                contests.append(contest)
        return contests

    async def get_team_in_contest(self, contest_id: str, team_id: str) -> TeamContest:
        """
        Return the TeamContest state for a specific team in a specific contest.
        Used for the team dashboard view (currency, score, registration info).

        Raises:
            ContestNotFoundException: If contest does not exist.
            TeamNotFoundException: If team does not exist.
            ContestNotFoundException: If the team is not registered.
        """
        await self.get_contest(contest_id)  # validates contest exists
        await self._team_service.get_team(team_id)  # validates team exists

        registration = await self._team_contest_dao.get(
            team_id=team_id, contest_id=contest_id
        )
        if not registration:
            raise ContestNotFoundException(
                message=f"Team '{team_id}' is not registered for contest '{contest_id}'"
            )
        return registration

    async def get_contest_leaderboard(
        self, contest_id: str
    ) -> list[tuple[int, TeamContest]]:
        """
        Return all registered teams for a contest ranked by score desc,
        then currency desc as a tiebreaker.

        Returns:
            List of (rank, TeamContest) tuples, 1-indexed.
        """
        await self.get_contest(contest_id)  # validates existence

        registrations = await self._team_contest_dao.get_by_contest(contest_id)
        sorted_teams = sorted(
            registrations,
            key=lambda r: (r.score, r.currency),
            reverse=True,
        )
        return [(i + 1, tc) for i, tc in enumerate(sorted_teams)]

    async def get_team_in_contest_safe(
        self, contest_id: str, team_id: str
    ) -> TeamContest | None:
        """
        Non-raising version of get_team_in_contest.
        Returns None if the team is not registered — used for pre-checks like can-join.
        """
        return await self._team_contest_dao.get(team_id=team_id, contest_id=contest_id)


# ── Dependency ─────────────────────────────────────────────────────────────────


async def get_contest_service(
    contest_dao: ContestDAO = Depends(get_contest_dao),
    team_contest_dao: TeamContestDAO = Depends(get_team_contest_dao),
    team_service: TeamService = Depends(get_team_service),
) -> ContestService:
    return ContestService(
        contest_dao=contest_dao,
        team_contest_dao=team_contest_dao,
        team_service=team_service,
    )
