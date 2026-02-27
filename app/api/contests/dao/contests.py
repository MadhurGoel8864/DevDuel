"""Contests Data Access Object"""

import logging
from typing import Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.database.models.contests import Contest, TeamContest

logger = logging.getLogger(__name__)


class ContestDAO:
    """Data Access Object for Contest model."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        name: str,
        start_time: object,
        end_time: object,
        description: Optional[str] = None,
    ) -> Contest:
        try:
            contest = Contest(
                name=name,
                description=description,
                start_time=start_time,
                end_time=end_time,
            )
            self._session.add(contest)
            await self._session.commit()
            await self._session.refresh(contest)
            return contest
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to create contest: {e}")
            raise e

    async def get_by_id(self, contest_id: str) -> Optional[Contest]:
        try:
            result = await self._session.execute(
                select(Contest).where(Contest.id == contest_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get contest by id {contest_id}: {e}")
            raise e

    async def get_all(self) -> list[Contest]:
        try:
            result = await self._session.execute(select(Contest))
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get all contests: {e}")
            raise e

    async def get_active(self) -> list[Contest]:
        try:
            result = await self._session.execute(
                select(Contest).where(Contest.is_active.is_(True))
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get active contests: {e}")
            raise e


class TeamContestDAO:
    """Data Access Object for TeamContest join model."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def register(self, team_id: str, contest_id: str) -> TeamContest:
        try:
            registration = TeamContest(team_id=team_id, contest_id=contest_id)
            self._session.add(registration)
            await self._session.commit()
            await self._session.refresh(registration)
            return registration
        except Exception as e:
            await self._session.rollback()
            logger.error(
                f"Failed to register team {team_id} for contest {contest_id}: {e}"
            )
            raise e

    async def get(self, team_id: str, contest_id: str) -> Optional[TeamContest]:
        try:
            result = await self._session.execute(
                select(TeamContest).where(
                    TeamContest.team_id == team_id,
                    TeamContest.contest_id == contest_id,
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get team contest registration: {e}")
            raise e

    async def get_by_contest(self, contest_id: str) -> list[TeamContest]:
        try:
            result = await self._session.execute(
                select(TeamContest).where(TeamContest.contest_id == contest_id)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get registrations for contest {contest_id}: {e}")
            raise e

    async def get_by_team(self, team_id: str) -> list[TeamContest]:
        try:
            result = await self._session.execute(
                select(TeamContest).where(TeamContest.team_id == team_id)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get contests for team {team_id}: {e}")
            raise e


# ── Dependencies ───────────────────────────────────────────────────────────────


async def get_contest_dao(session: AsyncSession = Depends(get_db)) -> ContestDAO:
    return ContestDAO(session)


async def get_team_contest_dao(
    session: AsyncSession = Depends(get_db),
) -> TeamContestDAO:
    return TeamContestDAO(session)
