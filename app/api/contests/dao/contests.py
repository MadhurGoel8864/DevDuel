"""Contests Data Access Object"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import Depends
from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.enums import ContestStatus
from app.database.models.contests import Contest, TeamContest
from app.database.models.teams import TeamMember

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
        created_by: str,
        description: Optional[str] = None,
    ) -> Contest:
        try:
            contest = Contest(
                name=name,
                description=description,
                start_time=start_time,
                end_time=end_time,
                created_by=created_by,
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

    async def get_created_by(self, user_id: str, skip: int = 0, limit: int = 20) -> list[Contest]:
        """Return contests created by the given user, paginated."""
        try:
            result = await self._session.execute(
                select(Contest)
                .where(Contest.created_by == user_id)
                .order_by(Contest.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get contests created by user {user_id}: {e}")
            raise e

    async def count_created_by(self, user_id: str) -> int:
        try:
            result = await self._session.execute(
                select(func.count()).select_from(Contest).where(Contest.created_by == user_id)
            )
            return result.scalar_one()
        except Exception as e:
            logger.error(f"Failed to count contests created by user {user_id}: {e}")
            raise e

    async def get_all(self, skip: int = 0, limit: int = 20) -> list[Contest]:
        try:
            result = await self._session.execute(
                select(Contest).order_by(Contest.created_at.desc()).offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get all contests: {e}")
            raise e

    async def count_all(self) -> int:
        try:
            result = await self._session.execute(select(func.count()).select_from(Contest))
            return result.scalar_one()
        except Exception as e:
            logger.error(f"Failed to count all contests: {e}")
            raise e

    async def get_active(self, skip: int = 0, limit: int = 20) -> list[Contest]:
        """Return only contests with ACTIVE status."""
        try:
            result = await self._session.execute(
                select(Contest)
                .where(Contest.status == ContestStatus.ACTIVE)
                .order_by(Contest.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get active contests: {e}")
            raise e

    async def count_active(self) -> int:
        try:
            result = await self._session.execute(
                select(func.count()).select_from(Contest).where(Contest.status == ContestStatus.ACTIVE)
            )
            return result.scalar_one()
        except Exception as e:
            logger.error(f"Failed to count active contests: {e}")
            raise e

    async def update_status(
        self, contest: Contest, new_status: ContestStatus
    ) -> Contest:
        """Persist a status change on the given Contest inside a transaction."""
        try:
            contest.status = new_status
            self._session.add(contest)
            await self._session.commit()
            await self._session.refresh(contest)
            return contest
        except Exception as e:
            await self._session.rollback()
            logger.error(
                f"Failed to update contest {contest.id} status to {new_status}: {e}"
            )
            raise e

    async def update_contest(
        self,
        contest: Contest,
        name: Optional[str] = None,
        description: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Contest:
        """
        Partial update — only provided (non-None) fields are applied.
        Returns the updated Contest instance.
        """
        try:
            contest.name = name
            if description is not None:
                contest.description = description
            contest.start_time = start_time
            contest.end_time = end_time

            self._session.add(contest)
            await self._session.commit()
            await self._session.refresh(contest)
            return contest
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to update contest {contest.id}: {e}")
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

    async def get_active_registrations_by_contest(
        self, contest_id: str
    ) -> list[TeamContest]:
        """
        Return only is_active=TRUE registrations for a contest.
        Used for leaderboard — inactive teams are hidden.
        """
        try:
            result = await self._session.execute(
                select(TeamContest).where(
                    TeamContest.contest_id == contest_id,
                    TeamContest.is_active,
                )
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(
                f"Failed to get active registrations for contest {contest_id}: {e}"
            )
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

    async def get_active_contests_for_team(self, team_id: str) -> list[TeamContest]:
        """Return TeamContest rows where the associated contest has ACTIVE status.

        Used to guard team roster/deletion modifications.
        """
        try:

            result = await self._session.execute(
                select(TeamContest)
                .join(Contest, TeamContest.contest_id == Contest.id)
                .where(
                    TeamContest.team_id == team_id,
                    Contest.status == ContestStatus.ACTIVE,
                )
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get active contests for team {team_id}: {e}")
            raise e

    async def get_open_or_active_contests_for_team(
        self, team_id: str
    ) -> list[TeamContest]:
        """Return TeamContest rows where contest is REGISTRATION_OPEN or ACTIVE."""
        try:
            result = await self._session.execute(
                select(TeamContest)
                .join(Contest, TeamContest.contest_id == Contest.id)
                .where(
                    TeamContest.team_id == team_id,
                    Contest.status.in_(
                        [
                            ContestStatus.REGISTRATION_OPEN,
                            ContestStatus.ACTIVE,
                        ]
                    ),
                )
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get open/active contests for team {team_id}: {e}")
            raise e

    async def get_inactive_contests_for_team(self, team_id: str) -> list[TeamContest]:
        """Return TeamContest rows where is_active=FALSE for the given team."""
        try:
            result = await self._session.execute(
                select(TeamContest).where(
                    TeamContest.team_id == team_id,
                    TeamContest.is_active == False,  # noqa: E712
                )
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get inactive contests for team {team_id}: {e}")
            raise e

    async def set_inactive(self, team_id: str, contest_id: str) -> None:
        """Mark a team's registration as inactive for a contest."""
        try:
            tc = await self.get(team_id=team_id, contest_id=contest_id)
            if tc:
                tc.is_active = False
                self._session.add(tc)
                await self._session.commit()
        except Exception as e:
            await self._session.rollback()
            logger.error(
                f"Failed to set inactive for team {team_id} contest {contest_id}: {e}"
            )
            raise e

    async def set_active(self, team_id: str, contest_id: str) -> None:
        """Re-activate a team's registration for a contest."""
        try:
            tc = await self.get(team_id=team_id, contest_id=contest_id)
            if tc:
                tc.is_active = True
                self._session.add(tc)
                await self._session.commit()
        except Exception as e:
            await self._session.rollback()
            logger.error(
                f"Failed to set active for team {team_id} contest {contest_id}: {e}"
            )
            raise e

    async def has_member_overlap(self, team_id: str, contest_id: str) -> bool:
        """
        Check if any member of team_id is already in contest_id via another team.
        Uses EXISTS query for efficiency.
        """
        try:
            stmt = exists().where(
                TeamContest.contest_id == contest_id,
                TeamContest.team_id != team_id,
                TeamMember.team_id == TeamContest.team_id,
                TeamMember.user_id.in_(
                    select(TeamMember.user_id).where(TeamMember.team_id == team_id)
                ),
            )
            result = await self._session.execute(select(stmt))
            return result.scalar()
        except Exception as e:
            logger.error(f"Failed to check member overlap: {e}")
            raise e

    async def has_member_in_active_contest(self, team_id: str) -> bool:
        """
        Check if any member of the team is already in an ACTIVE contest.
        Enforces one-active-contest rule per user.
        """
        try:
            stmt = exists().where(
                TeamContest.team_id != team_id,
                TeamContest.is_active,
                TeamMember.team_id == TeamContest.team_id,
                Contest.id == TeamContest.contest_id,
                Contest.status == ContestStatus.ACTIVE,
                TeamMember.user_id.in_(
                    select(TeamMember.user_id).where(TeamMember.team_id == team_id)
                ),
            )
            result = await self._session.execute(select(stmt))
            return result.scalar()
        except Exception as e:
            logger.error(f"Failed to check active contest for team {team_id}: {e}")
            raise e

    async def count_teams_per_contest(self, contest_ids: list[str]) -> dict[str, int]:
        """Return {contest_id: team_count} for the given contest IDs. Missing IDs → 0."""
        if not contest_ids:
            return {}
        try:
            result = await self._session.execute(
                select(TeamContest.contest_id, func.count(TeamContest.team_id))
                .where(TeamContest.contest_id.in_(contest_ids))
                .group_by(TeamContest.contest_id)
            )
            return dict(result.all())
        except Exception as e:
            logger.error(f"Failed to count teams per contest: {e}")
            raise e

    async def get_registered_team_ids(self, contest_id: str) -> list[str]:
        """Return all team_ids registered for a contest."""
        try:
            result = await self._session.execute(
                select(TeamContest.team_id).where(TeamContest.contest_id == contest_id)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(
                f"Failed to get registered team ids for contest {contest_id}: {e}"
            )
            raise e

    async def get_contest_user_ids(self, contest_id: str) -> set[str]:
        """Return all user_ids across all teams registered for a contest."""
        try:
            result = await self._session.execute(
                select(TeamMember.user_id)
                .join(TeamContest, TeamMember.team_id == TeamContest.team_id)
                .where(TeamContest.contest_id == contest_id)
            )
            return set(result.scalars().all())
        except Exception as e:
            logger.error(
                f"Failed to get contest user ids for contest {contest_id}: {e}"
            )
            raise e


# ── Dependencies ───────────────────────────────────────────────────────────────


async def get_contest_dao(session: AsyncSession = Depends(get_db)) -> ContestDAO:
    return ContestDAO(session)


async def get_team_contest_dao(
    session: AsyncSession = Depends(get_db),
) -> TeamContestDAO:
    return TeamContestDAO(session)
