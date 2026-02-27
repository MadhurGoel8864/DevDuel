"""Teams Data Access Object"""

import logging
from typing import Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.enums import TeamRole
from app.database.models.teams import Team, TeamMember

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

    async def remove(self, member: TeamMember) -> None:
        try:
            await self._session.delete(member)
            await self._session.commit()
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to remove team member: {e}")
            raise e


# ── Dependencies ───────────────────────────────────────────────────────────────


async def get_team_dao(session: AsyncSession = Depends(get_db)) -> TeamDAO:
    return TeamDAO(session)


async def get_team_member_dao(session: AsyncSession = Depends(get_db)) -> TeamMemberDAO:
    return TeamMemberDAO(session)
