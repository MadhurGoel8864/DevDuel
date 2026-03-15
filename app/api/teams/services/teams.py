"""Team Service Layer"""

import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends

from app.api.contests.dao.contests import TeamContestDAO, get_team_contest_dao
from app.api.teams.dao.teams import (
    TeamDAO,
    TeamMemberDAO,
    get_team_dao,
    get_team_member_dao,
)
from app.core.enums import ContestStatus, TeamRole
from app.core.exceptions.teams import (CannotLeaveOwnTeamException,
                                       CannotModifyTeamDuringActiveContest,
                                       NotTeamCreatorException,
                                       TeamAlreadyExistsException,
                                       TeamMemberAlreadyExistsException,
                                       TeamMemberNotFoundException,
                                       TeamMemberSameRoleException,
                                       TeamNotFoundException,
                                       TeamNotReadyForSwapException,
                                       TeamRoleTakenException)
from app.database.models.teams import Team, TeamMember

logger = logging.getLogger(__name__)


@dataclass
class TeamStatus:
    """
    Represents the readiness state of a team for contest participation.
    This is the single source of truth — reused by can_join_contest.
    """

    has_bidder: bool
    has_coder: bool
    member_count: int

    @property
    def is_ready(self) -> bool:
        """Team is contest-ready when both roles are filled."""
        return self.has_bidder and self.has_coder

    @property
    def missing_roles(self) -> list[str]:
        missing = []
        if not self.has_bidder:
            missing.append(TeamRole.BIDDING.value)
        if not self.has_coder:
            missing.append(TeamRole.CODING.value)
        return missing


class TeamService:
    """Business logic for Team operations."""

    def __init__(
        self,
        team_dao: TeamDAO,
        member_dao: TeamMemberDAO,
        team_contest_dao: TeamContestDAO,
    ):
        self._team_dao = team_dao
        self._member_dao = member_dao
        self._team_contest_dao = team_contest_dao

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _ensure_not_in_active_contest(self, team_id: str) -> None:
        """Raise CannotModifyTeamDuringActiveContest if team is in any ACTIVE contest."""
        active_entries = await self._team_contest_dao.get_active_contests_for_team(
            team_id
        )
        if active_entries:
            # Surface the first active contest id for context
            raise CannotModifyTeamDuringActiveContest(
                team_id=team_id,
                contest_id=active_entries[0].contest_id,
            )

    async def _handle_member_departure(self, team_id: str, member: TeamMember) -> None:
        """
        Core logic for a member leaving or being removed.

        If team is in REGISTRATION_OPEN or ACTIVE contest:
          → delete member row + mark all affected contests inactive

        Otherwise:
          → delete member row normally
        """
        affected_contests = (
            await self._team_contest_dao.get_open_or_active_contests_for_team(team_id)
        )

        await self._member_dao.remove(member)
        logger.info(f"Removed user {member.user_id} from team {team_id}")

        if affected_contests:
            for tc in affected_contests:
                await self._team_contest_dao.set_inactive(
                    team_id=team_id,
                    contest_id=tc.contest_id,
                )
            logger.info(
                f"Team {team_id} marked inactive for "
                f"{len(affected_contests)} contest(s) due to member departure"
            )

    async def _reactivate_if_complete(self, team_id: str) -> None:
        """
        Called after a new member joins.
        If team is now complete (1B + 1C) → re-activate any inactive contest registrations.
        """
        status = await self.get_team_status(team_id)
        if not status.is_ready:
            return

        inactive_contests = await self._team_contest_dao.get_inactive_contests_for_team(
            team_id
        )
        for tc in inactive_contests:
            await self._team_contest_dao.set_active(
                team_id=team_id,
                contest_id=tc.contest_id,
            )

        if inactive_contests:
            logger.info(
                f"Team {team_id} re-activated for "
                f"{len(inactive_contests)} contest(s) — roster is complete again"
            )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_team(self, name: str, creator_user_id: str) -> Team:
        """
        Create a new team and auto-add the creator as a BIDDING member.

        Args:
            name: Unique team name.
            creator_user_id: User ID of the creator.

        Returns:
            Created Team instance (with members eagerly loaded).

        Raises:
            TeamAlreadyExistsException: If a team with that name already exists.
        """
        logger.info(f"Creating team '{name}' for user {creator_user_id}")

        existing = await self._team_dao.get_by_name(name)
        if existing:
            raise TeamAlreadyExistsException(name=name)

        team = await self._team_dao.create(name=name, created_by=creator_user_id)

        # Auto-add creator as BIDDING member
        await self._member_dao.add(
            team_id=team.id,
            user_id=creator_user_id,
            role=TeamRole.BIDDING,
        )

        logger.info(f"Team '{name}' created with id {team.id}")
        # Re-fetch to include members relationship
        refreshed = await self._team_dao.get_by_id(team.id)
        return refreshed  # type: ignore[return-value]

    async def get_team(self, team_id: str) -> Team:
        """
        Get a team by ID.

        Raises:
            TeamNotFoundException: If team does not exist.
        """
        team = await self._team_dao.get_by_id(team_id)
        if not team:
            raise TeamNotFoundException(team_id=team_id)
        return team

    async def get_my_teams(self, user_id: str) -> list[Team]:
        """
        Get all teams the user is a member of.
        """
        team_ids = await self._member_dao.get_teams_for_user(user_id)
        teams = []
        for team_id in team_ids:
            team = await self._team_dao.get_by_id(team_id)
            if team:
                teams.append(team)
        return teams

    async def add_member(
        self,
        team_id: str,
        user_id: str,
        role: TeamRole,
        requesting_user_id: str,
    ) -> TeamMember:
        """
        Add a member to a team (creator only).

        Raises:
            TeamNotFoundException: If team does not exist.
            NotTeamCreatorException: If requester is not the team creator.
            CannotModifyTeamDuringActiveContest: If team is in an ACTIVE contest.
            TeamMemberAlreadyExistsException: If user is already a member.
            TeamRoleTakenException: If the role slot is already filled.
        """
        team = await self.get_team(team_id)

        if team.created_by != requesting_user_id:
            raise NotTeamCreatorException()

        # Guard: cannot modify roster during an active contest
        await self._ensure_not_in_active_contest(team_id)

        existing_member = await self._member_dao.get(team_id=team_id, user_id=user_id)
        if existing_member:
            raise TeamMemberAlreadyExistsException(user_id=user_id, team_id=team_id)

        role_count = await self._member_dao.count_by_role(team_id=team_id, role=role)
        if role_count > 0:
            raise TeamRoleTakenException(role=role.value)

        member = await self._member_dao.add(team_id=team_id, user_id=user_id, role=role)
        logger.info(f"Added user {user_id} to team {team_id} as {role.value}")

        await self._reactivate_if_complete(team_id)
        return member

    async def remove_member(
        self,
        team_id: str,
        user_id: str,
        requesting_user_id: str,
    ) -> None:
        """
        Remove a member from a team (creator only, cannot remove themselves).

        Raises:
            TeamNotFoundException: If team does not exist.
            NotTeamCreatorException: If requester is not the team creator.
            CannotModifyTeamDuringActiveContest: If team is in an ACTIVE contest.
            TeamMemberNotFoundException: If the target user is not a member.
        """
        team = await self.get_team(team_id)

        if team.created_by != requesting_user_id:
            raise NotTeamCreatorException()

        if user_id == requesting_user_id:
            raise NotTeamCreatorException(
                message="Team creator cannot remove themselves from the team"
            )

        # Guard: cannot modify roster during an active contest
        await self._ensure_not_in_active_contest(team_id)

        member = await self._member_dao.get(team_id=team_id, user_id=user_id)
        if not member:
            raise TeamMemberNotFoundException(user_id=user_id, team_id=team_id)

        await self._handle_member_departure(team_id=team_id, member=member)

    async def leave_team(self, team_id: str, requesting_user_id: str) -> None:
        team = await self.get_team(team_id)

        if team.created_by == requesting_user_id:
            raise CannotLeaveOwnTeamException(team_id=team_id)

        member = await self._member_dao.get(team_id=team_id, user_id=requesting_user_id)
        if not member:
            raise TeamMemberNotFoundException(
                user_id=requesting_user_id, team_id=team_id
            )

        await self._handle_member_departure(team_id=team_id, member=member)
        logger.info(f"User {requesting_user_id} left team {team_id}")

    async def swap_member_roles(
        self,
        team_id: str,
        requesting_user_id: str,
    ) -> Team:
        """
        Swap roles of the two team members (creator only).

        No input needed — team has exactly 2 members (1 BIDDING + 1 CODING).
        Both members are auto-fetched from the team.

        Raises:
            TeamNotFoundException, NotTeamCreatorException,
            CannotModifyTeamDuringActiveContest,
            TeamNotReadyForSwapException: If team doesn't have exactly 2 members.
            TeamMemberSameRoleException: If both members have the same role (shouldn't happen).
        """
        team = await self.get_team(team_id)

        if team.created_by != requesting_user_id:
            raise NotTeamCreatorException()

        # Guard: cannot swap roles during an active contest
        await self._ensure_not_in_active_contest(team_id)

        # Fetch all members — must be exactly 2
        members = await self._member_dao.get_by_team(team_id)
        if len(members) != 2:
            raise TeamNotReadyForSwapException(
                team_id=team_id,
                member_count=len(members),
            )

        member1, member2 = members[0], members[1]

        # No-op guard — roles must be different to swap
        if member1.role == member2.role:
            raise TeamMemberSameRoleException(role=member1.role.value)

        await self._member_dao.swap_roles(member1, member2)
        logger.info(
            f"Swapped roles between members {member1.user_id} and {member2.user_id} in team {team_id}"
        )

        refreshed = await self._team_dao.get_by_id(team_id)
        return refreshed  # type: ignore[return-value]

    async def delete_team(self, team_id: str, requesting_user_id: str) -> None:
        """
        Delete a team (creator only). Cascades to members and contest registrations.

        Raises:
            TeamNotFoundException: If team does not exist.
            NotTeamCreatorException: If requester is not the team creator.
            CannotModifyTeamDuringActiveContest: If team is in an ACTIVE contest.
        """
        team = await self.get_team(team_id)

        if team.created_by != requesting_user_id:
            raise NotTeamCreatorException()

        # Guard: cannot delete a team that is in an active contest
        await self._ensure_not_in_active_contest(team_id)

        await self._team_dao.delete(team)
        logger.info(f"Deleted team {team_id}")

    async def get_team_status(self, team_id: str) -> TeamStatus:
        """
        Determine whether the team is contest-ready.

        A team is ready when it has exactly one BIDDING and one CODING member.
        This is the authoritative readiness check — other methods must call this
        rather than reimplement the logic.

        Raises:
            TeamNotFoundException: If team does not exist.
        """
        await self.get_team(team_id)  # validates existence

        has_bidder = await self._member_dao.count_by_role(team_id, TeamRole.BIDDING) > 0
        has_coder = await self._member_dao.count_by_role(team_id, TeamRole.CODING) > 0
        members = await self._member_dao.get_by_team(team_id)

        return TeamStatus(
            has_bidder=has_bidder,
            has_coder=has_coder,
            member_count=len(members),
        )

    async def get_team_member_user_ids(self, team_id: str) -> set[str]:
        await self.get_team(team_id)
        members = await self._member_dao.get_by_team(team_id)
        return {m.user_id for m in members}

    async def get_user_role_in_team(
        self, team_id: str, user_id: str
    ) -> Optional[TeamRole]:
        """
        Return the role of a user in a team, or None if not a member.

        Raises:
            TeamNotFoundException: If team does not exist.
        """
        await self.get_team(team_id)  # validates existence
        member = await self._member_dao.get(team_id=team_id, user_id=user_id)
        return member.role if member else None

    async def can_join_contest(
        self,
        team_id: str,
        contest_status: ContestStatus,
        already_registered: bool,
        contest_member_user_ids: set[str] | None = None,
    ) -> tuple[bool, list[str]]:
        reasons: list[str] = []

        # Reuse the single source of truth for team readiness
        status = await self.get_team_status(team_id)
        if not status.is_ready:
            reasons.append(f"Team is missing roles: {', '.join(status.missing_roles)}")

        if contest_status != ContestStatus.REGISTRATION_OPEN:
            reasons.append(
                f"Contest registration is not open (status: {contest_status.value})"
            )

        if already_registered:
            reasons.append("Team is already registered for this contest")

        if contest_member_user_ids is not None:
            team_user_ids = await self.get_team_member_user_ids(team_id)
            overlapping = team_user_ids & contest_member_user_ids
            if overlapping:
                reasons.append(
                    f"Team member(s) already in this contest via another team: "
                    f"{', '.join(overlapping)}"
                )

        return (len(reasons) == 0, reasons)


# ── Dependency ─────────────────────────────────────────────────────────────────


async def get_team_service(
    team_dao: TeamDAO = Depends(get_team_dao),
    member_dao: TeamMemberDAO = Depends(get_team_member_dao),
    team_contest_dao: TeamContestDAO = Depends(get_team_contest_dao),
) -> TeamService:
    return TeamService(
        team_dao=team_dao,
        member_dao=member_dao,
        team_contest_dao=team_contest_dao,
    )
