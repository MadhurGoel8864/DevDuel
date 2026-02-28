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
from app.core.exceptions.contests import (
    ContestAlreadyRegisteredException,
    ContestNotActiveException,
    ContestNotFoundException,
)
from app.core.exceptions.teams import NotTeamCreatorException
from app.database.models.contests import Contest, TeamContest

logger = logging.getLogger(__name__)


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
        description: str | None = None,
    ) -> Contest:
        """
        Create a new contest.

        Args:
            name: Contest name.
            start_time: Contest start datetime.
            end_time: Contest end datetime.
            description: Optional description.

        Returns:
            Created Contest instance.
        """
        logger.info(f"Creating contest '{name}'")
        contest = await self._contest_dao.create(
            name=name,
            description=description,
            start_time=start_time,
            end_time=end_time,
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
        """Return only active contests."""
        return await self._contest_dao.get_active()

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
            ContestNotActiveException: If contest is not active.
            NotTeamCreatorException: If requester is not the team creator.
            ContestAlreadyRegisteredException: If team is already registered.
        """
        contest = await self.get_contest(contest_id)

        if not contest.is_active:
            raise ContestNotActiveException(contest_id=contest_id)

        # Validate team exists and requesting user is its creator
        team = await self._team_service.get_team(team_id=team_id)
        if team.created_by != requesting_user_id:
            raise NotTeamCreatorException(
                message="Only the team creator can register the team for a contest"
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

    async def get_my_contests(self, user_id: str) -> list[Contest]:
        """
        Get all contests that any of the user's teams are participating in.
        """
        # Get team_ids the user belongs to
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
            ContestAlreadyRegisteredException: Reused as NotFoundException here
                — raises if the team is not registered.
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
