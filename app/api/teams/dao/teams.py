"""Teams Data Access Object"""

import logging
from typing import Optional

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.enums import JoinRequestStatus, TeamRole
from app.database.models.teams import Team, TeamJoinRequest, TeamMember

logger = logging.getLogger(__name__)


class TeamDAO:
    """Data Access Object for Team model."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, name: str, created_by: str) -> Team:
        try:
            team = Team(name=name, created_by=created_by)
            self._session.add(team)
            await self._session.commit()
            await self._session.refresh(team)
            return team
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to create team: {e}")
            raise e

    async def get_by_id(self, team_id: str) -> Optional[Team]:
        try:
            result = await self._session.execute(select(Team).where(Team.id == team_id))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get team by id {team_id}: {e}")
            raise e

    async def get_by_name(self, name: str) -> Optional[Team]:
        try:
            result = await self._session.execute(select(Team).where(Team.name == name))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get team by name {name}: {e}")
            raise e

    async def delete(self, team: Team) -> None:
        try:
            await self._session.delete(team)
            await self._session.commit()
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to delete team {team.id}: {e}")
            raise e

    async def get_browseable_for_user(
        self, user_id: str, limit: int, offset: int
    ) -> tuple[list[Team], int]:
        """
        Return paginated teams the user is NOT already a member of.
        Members are eagerly loaded so callers can compute open slots.

        Returns:
            (teams, total_count)
        """
        try:
            user_team_ids_subq = (
                select(TeamMember.team_id).where(TeamMember.user_id == user_id)
            ).subquery()

            base_filter = ~Team.id.in_(select(user_team_ids_subq.c.team_id))

            total_result = await self._session.execute(
                select(func.count()).select_from(Team).where(base_filter)
            )
            total = int(total_result.scalar_one())

            list_result = await self._session.execute(
                select(Team)
                .where(base_filter)
                .options(selectinload(Team.members))
                .order_by(Team.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            teams = list(list_result.scalars().all())
            return teams, total
        except Exception as e:
            logger.error(f"Failed to get browseable teams for user {user_id}: {e}")
            raise e


class TeamMemberDAO:
    """Data Access Object for TeamMember model."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, team_id: str, user_id: str, role: TeamRole) -> TeamMember:
        try:
            member = TeamMember(team_id=team_id, user_id=user_id, role=role)
            self._session.add(member)
            await self._session.commit()
            await self._session.refresh(member)
            return member
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to add team member: {e}")
            raise e

    async def get(self, team_id: str, user_id: str) -> Optional[TeamMember]:
        try:
            result = await self._session.execute(
                select(TeamMember).where(
                    TeamMember.team_id == team_id,
                    TeamMember.user_id == user_id,
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get team member: {e}")
            raise e

    async def get_by_id(self, member_id: str) -> Optional[TeamMember]:
        try:
            result = await self._session.execute(
                select(TeamMember).where(TeamMember.id == member_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get team member by id {member_id}: {e}")
            raise e

    async def get_by_team(self, team_id: str) -> list[TeamMember]:
        try:
            result = await self._session.execute(
                select(TeamMember).where(TeamMember.team_id == team_id)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get members for team {team_id}: {e}")
            raise e

    async def get_teams_for_user(self, user_id: str) -> list[str]:
        """Return list of team_ids the user belongs to."""
        try:
            result = await self._session.execute(
                select(TeamMember.team_id).where(TeamMember.user_id == user_id)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get teams for user {user_id}: {e}")
            raise e

    async def count_members_per_team(self, team_ids: list[str]) -> dict[str, int]:
        """Return {team_id: member_count} for the given team IDs. Missing IDs → 0."""
        if not team_ids:
            return {}
        try:
            result = await self._session.execute(
                select(TeamMember.team_id, func.count(TeamMember.id))
                .where(TeamMember.team_id.in_(team_ids))
                .group_by(TeamMember.team_id)
            )
            return dict(result.all())
        except Exception as e:
            logger.error(f"Failed to count members per team: {e}")
            raise e

    async def count_teams_for_user(self, user_id: str) -> int:
        """Return the total number of teams the user belongs to."""
        try:
            result = await self._session.execute(
                select(func.count()).select_from(TeamMember).where(TeamMember.user_id == user_id)
            )
            return result.scalar_one()
        except Exception as e:
            logger.error(f"Failed to count teams for user {user_id}: {e}")
            raise e

    async def get_teams_for_user_paginated(
        self, user_id: str, limit: int, offset: int
    ) -> list[str]:
        """Return paginated list of team_ids the user belongs to."""
        try:
            result = await self._session.execute(
                select(TeamMember.team_id)
                .where(TeamMember.user_id == user_id)
                .order_by(TeamMember.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get paginated teams for user {user_id}: {e}")
            raise e

    async def count_by_role(self, team_id: str, role: TeamRole) -> int:
        try:
            result = await self._session.execute(
                select(TeamMember).where(
                    TeamMember.team_id == team_id,
                    TeamMember.role == role,
                )
            )
            return len(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to count members by role: {e}")
            raise e

    async def swap_roles(
        self, member1: TeamMember, member2: TeamMember
    ) -> tuple[TeamMember, TeamMember]:
        """
        Atomically swap the roles of two TeamMember records.
        Rolls back both changes if anything fails.
        """
        try:
            member1.role, member2.role = (
                member2.role,
                member1.role,
            )  # Swap roles in memory
            self._session.add(member1)
            self._session.add(member2)
            await self._session.commit()
            await self._session.refresh(member1)
            await self._session.refresh(member2)
            return member1, member2
        except Exception as e:
            await self._session.rollback()
            logger.error(
                f"Failed to swap roles between {member1.id} and {member2.id}: {e}"
            )
            raise e

    async def remove(self, member: TeamMember) -> None:
        try:
            await self._session.delete(member)
            await self._session.commit()
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to remove team member: {e}")
            raise e


class TeamJoinRequestDAO:
    """Data Access Object for TeamJoinRequest model."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self, team_id: str, user_id: str, role: TeamRole
    ) -> TeamJoinRequest:
        try:
            req = TeamJoinRequest(
                team_id=team_id,
                user_id=user_id,
                role=role,
                status=JoinRequestStatus.PENDING,
            )
            self._session.add(req)
            await self._session.commit()
            await self._session.refresh(req)
            return req
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to create join request: {e}")
            raise e

    async def get_by_id(self, request_id: str) -> Optional[TeamJoinRequest]:
        try:
            result = await self._session.execute(
                select(TeamJoinRequest)
                .where(TeamJoinRequest.id == request_id)
                .options(
                    selectinload(TeamJoinRequest.team),
                    selectinload(TeamJoinRequest.user),
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get join request {request_id}: {e}")
            raise e

    async def get_pending_for_user(self, user_id: str) -> Optional[TeamJoinRequest]:
        """Return the user's currently pending request (if any)."""
        try:
            result = await self._session.execute(
                select(TeamJoinRequest)
                .where(
                    TeamJoinRequest.user_id == user_id,
                    TeamJoinRequest.status == JoinRequestStatus.PENDING,
                )
                .options(selectinload(TeamJoinRequest.team))
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get pending join request for user {user_id}: {e}")
            raise e

    async def get_pending_for_team(self, team_id: str) -> list[TeamJoinRequest]:
        try:
            result = await self._session.execute(
                select(TeamJoinRequest)
                .where(
                    TeamJoinRequest.team_id == team_id,
                    TeamJoinRequest.status == JoinRequestStatus.PENDING,
                )
                .options(selectinload(TeamJoinRequest.user))
                .order_by(TeamJoinRequest.created_at.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to list pending join requests for team {team_id}: {e}")
            raise e

    async def get_all_for_user(self, user_id: str) -> list[TeamJoinRequest]:
        try:
            result = await self._session.execute(
                select(TeamJoinRequest)
                .where(TeamJoinRequest.user_id == user_id)
                .options(selectinload(TeamJoinRequest.team))
                .order_by(TeamJoinRequest.created_at.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to list join requests for user {user_id}: {e}")
            raise e

    async def update_status(
        self, req: TeamJoinRequest, status: JoinRequestStatus
    ) -> TeamJoinRequest:
        try:
            req.status = status
            self._session.add(req)
            await self._session.commit()
            await self._session.refresh(req)
            return req
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to update join request {req.id} status: {e}")
            raise e

    async def cancel_other_pending_for_user(
        self, user_id: str, except_request_id: str
    ) -> int:
        """Bulk-cancel all other pending requests of a user (used after acceptance)."""
        try:
            result = await self._session.execute(
                select(TeamJoinRequest).where(
                    TeamJoinRequest.user_id == user_id,
                    TeamJoinRequest.status == JoinRequestStatus.PENDING,
                    TeamJoinRequest.id != except_request_id,
                )
            )
            others = list(result.scalars().all())
            for r in others:
                r.status = JoinRequestStatus.CANCELLED
                self._session.add(r)
            if others:
                await self._session.commit()
            return len(others)
        except Exception as e:
            await self._session.rollback()
            logger.error(
                f"Failed to cancel other pending requests for user {user_id}: {e}"
            )
            raise e


# ── Dependencies ───────────────────────────────────────────────────────────────


async def get_team_dao(session: AsyncSession = Depends(get_db)) -> TeamDAO:
    return TeamDAO(session)


async def get_team_member_dao(session: AsyncSession = Depends(get_db)) -> TeamMemberDAO:
    return TeamMemberDAO(session)


async def get_team_join_request_dao(
    session: AsyncSession = Depends(get_db),
) -> TeamJoinRequestDAO:
    return TeamJoinRequestDAO(session)
