"""Team Service Layer"""

import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends

from app.api.teams.dao.teams import (
    TeamDAO,
    TeamMemberDAO,
    get_team_dao,
    get_team_member_dao,
)
from app.core.enums import TeamRole
from app.core.exceptions.teams import (
    NotTeamCreatorException,
    TeamAlreadyExistsException,
    TeamMemberAlreadyExistsException,
    TeamMemberNotFoundException,
    TeamNotFoundException,
    TeamRoleTakenException,
    TeamMemberSameRoleException,
)
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

    def __init__(self, team_dao: TeamDAO, member_dao: TeamMemberDAO):
        self._team_dao = team_dao
        self._member_dao = member_dao

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
            TeamMemberAlreadyExistsException: If user is already a member.
            TeamRoleTakenException: If the role slot is already filled.
        """
        team = await self.get_team(team_id)

        if team.created_by != requesting_user_id:
            raise NotTeamCreatorException()

        existing_member = await self._member_dao.get(team_id=team_id, user_id=user_id)
        if existing_member:
            raise TeamMemberAlreadyExistsException(user_id=user_id, team_id=team_id)

        role_count = await self._member_dao.count_by_role(team_id=team_id, role=role)
        if role_count > 0:
            raise TeamRoleTakenException(role=role.value)

        member = await self._member_dao.add(team_id=team_id, user_id=user_id, role=role)
        logger.info(f"Added user {user_id} to team {team_id} as {role.value}")
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
            NotTeamCreatorException: If creator tries to remove themselves.
            TeamMemberNotFoundException: If the target user is not a member.
        """
        team = await self.get_team(team_id)

        if team.created_by != requesting_user_id:
            raise NotTeamCreatorException()

        if user_id == requesting_user_id:
            raise NotTeamCreatorException(
                message="Team creator cannot remove themselves from the team"
            )

        member = await self._member_dao.get(team_id=team_id, user_id=user_id)
        if not member:
            raise TeamMemberNotFoundException(user_id=user_id, team_id=team_id)

        await self._member_dao.remove(member)
        logger.info(f"Removed user {user_id} from team {team_id}")

    async def swap_member_roles(
        self,
        team_id: str,
        member1_id: str,
        member2_id: str,
        requesting_user_id: str,
    ) -> Team:
        """
        Swap the roles of two members within a team (creator only).

        Args:
            team_id: The team both members belong to.
            member1_id: TeamMember.id of the first member.
            member2_id: TeamMember.id of the second member.
            requesting_user_id: Must be the team creator.

        Returns:
            Updated Team instance with refreshed members.

        Raises:
            TeamNotFoundException: If team does not exist.
            NotTeamCreatorException: If requester is not the team creator.
            TeamMemberNotFoundException: If either member ID is not found in this team.
            TeamMemberSameRoleException: If both members already have the same role.
        """
        team = await self.get_team(team_id)

        if team.created_by != requesting_user_id:
            raise NotTeamCreatorException()

        # Fetch both members by their TeamMember.id and verify they belong to this team
        member1 = await self._member_dao.get_by_id(member1_id)
        if not member1 or member1.team_id != team_id:
            raise TeamMemberNotFoundException(user_id=member1_id, team_id=team_id)

        member2 = await self._member_dao.get_by_id(member2_id)
        if not member2 or member2.team_id != team_id:
            raise TeamMemberNotFoundException(user_id=member2_id, team_id=team_id)

        # No-op guard — roles are already different, nothing to swap
        if member1.role == member2.role:
            raise TeamMemberSameRoleException(role=member1.role.value)

        await self._member_dao.swap_roles(member1, member2)
        logger.info(
            f"Swapped roles between members {member1_id} and {member2_id} in team {team_id}"
        )

        refreshed = await self._team_dao.get_by_id(team_id)
        return refreshed  # type: ignore[return-value]

    async def delete_team(self, team_id: str, requesting_user_id: str) -> None:
        """
        Delete a team (creator only). Cascades to members and contest registrations.

        Raises:
            TeamNotFoundException: If team does not exist.
            NotTeamCreatorException: If requester is not the team creator.
        """
        team = await self.get_team(team_id)

        if team.created_by != requesting_user_id:
            raise NotTeamCreatorException()

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
        contest_is_active: bool,
        already_registered: bool,
    ) -> tuple[bool, list[str]]:
        """
        Pre-check whether a team can join a contest.

        Reuses get_team_status() — no readiness logic is reimplemented here.

        Args:
            team_id: Team to check.
            contest_is_active: Whether the target contest is active.
            already_registered: Whether the team is already in the contest.

        Returns:
            Tuple of (can_join: bool, reasons: list[str]).
            `reasons` is empty when can_join is True.

        Raises:
            TeamNotFoundException: If team does not exist.
        """
        reasons: list[str] = []

        # Reuse the single source of truth for team readiness
        status = await self.get_team_status(team_id)
        if not status.is_ready:
            reasons.append(f"Team is missing roles: {', '.join(status.missing_roles)}")

        if not contest_is_active:
            reasons.append("Contest is not active")

        if already_registered:
            reasons.append("Team is already registered for this contest")

        return (len(reasons) == 0, reasons)


# ── Dependency ─────────────────────────────────────────────────────────────────


async def get_team_service(
    team_dao: TeamDAO = Depends(get_team_dao),
    member_dao: TeamMemberDAO = Depends(get_team_member_dao),
) -> TeamService:
    return TeamService(team_dao=team_dao, member_dao=member_dao)