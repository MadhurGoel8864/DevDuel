"""Problems Data Access Object"""

import logging
from typing import Optional

from fastapi import Depends
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.enums import Difficulty
from app.database.models.contests import Contest
from app.database.models.problems import BuiltinProblem, ContestProblem

logger = logging.getLogger(__name__)


class BuiltinProblemDAO:
    """Data Access Object for BuiltinProblem model."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, builtin_problem_id: str) -> Optional[BuiltinProblem]:
        result = await self._session.execute(
            select(BuiltinProblem).where(BuiltinProblem.id == builtin_problem_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        difficulty: Optional[Difficulty] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 10,
    ) -> list[BuiltinProblem]:
        query = select(BuiltinProblem).where(
            BuiltinProblem.is_active == True  # noqa: E712
        )
        if difficulty is not None:
            query = query.where(BuiltinProblem.difficulty == difficulty)
        if search:
            query = query.where(BuiltinProblem.title.ilike(f"%{search}%"))
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        difficulty: Optional[Difficulty] = None,
        search: Optional[str] = None,
    ) -> int:
        query = select(func.count(BuiltinProblem.id)).where(
            BuiltinProblem.is_active == True  # noqa: E712
        )
        if difficulty is not None:
            query = query.where(BuiltinProblem.difficulty == difficulty)
        if search:
            query = query.where(BuiltinProblem.title.ilike(f"%{search}%"))
        result = await self._session.execute(query)
        return result.scalar_one()


class ContestProblemDAO:
    """Data Access Object for ContestProblem join model."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_contest(self, contest_id: str) -> Optional[Contest]:
        """Return the Contest row or None."""
        result = await self._session.execute(
            select(Contest).where(Contest.id == contest_id)
        )
        return result.scalar_one_or_none()

    async def add(
        self,
        contest_id: str,
        problem_id: str,
        problem_order: int,
        difficulty: Difficulty,
        points: int,
        base_price: int,
        time_limit_ms: int,
        memory_limit_mb: int,
    ) -> ContestProblem:
        cp = ContestProblem(
            contest_id=contest_id,
            problem_id=problem_id,
            problem_order=problem_order,
            difficulty=difficulty,
            points=points,
            base_price=base_price,
            time_limit_ms=time_limit_ms,
            memory_limit_mb=memory_limit_mb,
        )
        self._session.add(cp)
        await self._session.commit()
        await self._session.refresh(cp)
        return cp

    async def list_by_contest(self, contest_id: str) -> list[ContestProblem]:
        """Return active ContestProblem rows for a contest, sorted by problem_order."""
        result = await self._session.execute(
            select(ContestProblem)
            .where(
                and_(
                    ContestProblem.contest_id == contest_id,
                    ContestProblem.is_active == True,  # noqa: E712
                )
            )
            .order_by(ContestProblem.problem_order)
        )
        return list(result.scalars().all())

    async def get_by_id(self, contest_problem_id: str) -> Optional[ContestProblem]:
        result = await self._session.execute(
            select(ContestProblem).where(ContestProblem.id == contest_problem_id)
        )
        return result.scalar_one_or_none()

    async def get_by_contest_and_problem(
        self, contest_id: str, problem_id: str
    ) -> Optional[ContestProblem]:
        result = await self._session.execute(
            select(ContestProblem).where(
                and_(
                    ContestProblem.contest_id == contest_id,
                    ContestProblem.problem_id == problem_id,
                    ContestProblem.is_active == True,  # noqa: E712
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_contest_and_order(
        self, contest_id: str, problem_order: int
    ) -> Optional[ContestProblem]:
        result = await self._session.execute(
            select(ContestProblem).where(
                and_(
                    ContestProblem.contest_id == contest_id,
                    ContestProblem.problem_order == problem_order,
                    ContestProblem.is_active == True,  # noqa: E712
                )
            )
        )
        return result.scalar_one_or_none()

    async def update(self, cp: ContestProblem, **kwargs) -> ContestProblem:
        for field, value in kwargs.items():
            if value is not None:
                setattr(cp, field, value)
        self._session.add(cp)
        await self._session.commit()
        await self._session.refresh(cp)
        return cp

    async def get_max_order(self, contest_id: str) -> int:
        """Return the highest problem_order for active problems in a contest, or 0."""
        result = await self._session.execute(
            select(func.coalesce(func.max(ContestProblem.problem_order), 0)).where(
                and_(
                    ContestProblem.contest_id == contest_id,
                    ContestProblem.is_active == True,  # noqa: E712
                )
            )
        )
        return result.scalar_one()

    async def resequence_orders(self, contest_id: str) -> None:
        """Resequence problem_order values (1, 2, 3, ...) for a contest, closing gaps."""
        problems = await self.list_by_contest(contest_id)
        for idx, cp in enumerate(problems, start=1):
            if cp.problem_order != idx:
                cp.problem_order = idx
                self._session.add(cp)
        await self._session.commit()

    async def delete(self, cp: ContestProblem) -> None:
        await self._session.delete(cp)
        await self._session.commit()


# ── Dependencies ────────────────────────────────────────────────────────────────


async def get_builtin_problem_dao(
    session: AsyncSession = Depends(get_db),
) -> BuiltinProblemDAO:
    return BuiltinProblemDAO(session)


async def get_contest_problem_dao(
    session: AsyncSession = Depends(get_db),
) -> ContestProblemDAO:
    return ContestProblemDAO(session)
