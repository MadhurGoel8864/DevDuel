"""Problems Data Access Object"""

import logging
from typing import Optional

from fastapi import Depends
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.enums import Difficulty
from app.database.models.problems import BuiltinProblem, ContestProblem, Problem

logger = logging.getLogger(__name__)


class ProblemDAO:
    """Data Access Object for Problem model."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        title: str,
        slug: str,
        description: str,
        difficulty: Difficulty,
        points: int,
        base_price: int,
        created_by: str,
        time_limit_ms: int = 2000,
        memory_limit_mb: int = 256,
    ) -> Problem:
        try:
            problem = Problem(
                title=title,
                slug=slug,
                description=description,
                difficulty=difficulty,
                points=points,
                base_price=base_price,
                time_limit_ms=time_limit_ms,
                memory_limit_mb=memory_limit_mb,
                created_by=created_by,
            )
            self._session.add(problem)
            await self._session.commit()
            await self._session.refresh(problem)
            return problem
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to create problem: {e}")
            raise e

    async def get_by_id(self, problem_id: str) -> Optional[Problem]:
        try:
            result = await self._session.execute(
                select(Problem).where(Problem.id == problem_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get problem by id {problem_id}: {e}")
            raise e

    async def get_by_slug(self, slug: str) -> Optional[Problem]:
        try:
            result = await self._session.execute(
                select(Problem).where(Problem.slug == slug)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get problem by slug {slug}: {e}")
            raise e

    async def slug_exists(self, slug: str) -> bool:
        """Check whether a slug is already in use."""
        result = await self._session.execute(
            select(Problem.id).where(Problem.slug == slug)
        )
        return result.scalar_one_or_none() is not None

    async def list_all(
        self,
        difficulty: Optional[Difficulty] = None,
        search: Optional[str] = None,
        created_by: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[Problem]:
        try:
            query = select(Problem).where(Problem.is_active == True)  # noqa: E712
            if difficulty is not None:
                query = query.where(Problem.difficulty == difficulty)
            if created_by is not None:
                query = query.where(Problem.created_by == created_by)
            if search:
                query = query.where(
                    or_(
                        Problem.title.ilike(f"%{search}%"),
                        Problem.description.ilike(f"%{search}%"),
                    )
                )
            offset = (page - 1) * limit
            query = query.offset(offset).limit(limit)
            result = await self._session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to list problems: {e}")
            raise e

    async def update(self, problem: Problem, **kwargs) -> Problem:
        try:
            for field, value in kwargs.items():
                if value is not None:
                    setattr(problem, field, value)
            self._session.add(problem)
            await self._session.commit()
            await self._session.refresh(problem)
            return problem
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to update problem {problem.id}: {e}")
            raise e

    async def soft_delete(self, problem: Problem) -> Problem:
        try:
            problem.is_active = False
            self._session.add(problem)
            await self._session.commit()
            await self._session.refresh(problem)
            return problem
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to soft-delete problem {problem.id}: {e}")
            raise e


class ContestProblemDAO:
    """Data Access Object for ContestProblem join model."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(
        self,
        contest_id: str,
        problem_id: str,
        problem_order: int,
    ) -> ContestProblem:
        try:
            cp = ContestProblem(
                contest_id=contest_id,
                problem_id=problem_id,
                problem_order=problem_order,
            )
            self._session.add(cp)
            await self._session.commit()
            await self._session.refresh(cp)
            return cp
        except Exception as e:
            await self._session.rollback()
            logger.error(
                f"Failed to add problem {problem_id} to contest {contest_id}: {e}"
            )
            raise e

    async def contest_exists(self, contest_id: str) -> bool:
        """Return True if a Contest row with the given id exists."""
        from sqlalchemy import select

        from app.database.models.contests import Contest

        try:
            result = await self._session.execute(
                select(Contest.id).where(Contest.id == contest_id)
            )
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Failed to check contest existence for {contest_id}: {e}")
            raise e

    async def list_by_contest(self, contest_id: str) -> list[ContestProblem]:
        """Return active ContestProblem rows for a contest, sorted by problem_order."""
        try:
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
        except Exception as e:
            logger.error(f"Failed to list problems for contest {contest_id}: {e}")
            raise e

    async def get_by_id(self, contest_problem_id: str) -> Optional[ContestProblem]:
        try:
            result = await self._session.execute(
                select(ContestProblem).where(ContestProblem.id == contest_problem_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get contest-problem {contest_problem_id}: {e}")
            raise e

    async def get_by_contest_and_problem(
        self, contest_id: str, problem_id: str
    ) -> Optional[ContestProblem]:
        try:
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
        except Exception as e:
            logger.error(f"Failed to query contest-problem: {e}")
            raise e

    async def get_by_contest_and_order(
        self, contest_id: str, problem_order: int
    ) -> Optional[ContestProblem]:
        try:
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
        except Exception as e:
            logger.error(f"Failed to query contest-problem by order: {e}")
            raise e

    async def soft_delete(self, cp: ContestProblem) -> ContestProblem:
        try:
            cp.is_active = False
            self._session.add(cp)
            await self._session.commit()
            await self._session.refresh(cp)
            return cp
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to soft-delete contest-problem {cp.id}: {e}")
            raise e


class BuiltinProblemDAO:
    """Data Access Object for BuiltinProblem model."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, builtin_problem_id: str) -> Optional[BuiltinProblem]:
        try:
            result = await self._session.execute(
                select(BuiltinProblem).where(BuiltinProblem.id == builtin_problem_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"Failed to get builtin problem by id {builtin_problem_id}: {e}"
            )
            raise e

    async def list_all(
        self,
        difficulty: Optional[Difficulty] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[BuiltinProblem]:
        try:
            query = select(BuiltinProblem).where(
                BuiltinProblem.is_active == True  # noqa: E712
            )
            if difficulty is not None:
                query = query.where(BuiltinProblem.difficulty == difficulty)
            if search:
                query = query.where(
                    or_(
                        BuiltinProblem.title.ilike(f"%{search}%"),
                        BuiltinProblem.description.ilike(f"%{search}%"),
                    )
                )
            offset = (page - 1) * limit
            query = query.offset(offset).limit(limit)
            result = await self._session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to list builtin problems: {e}")
            raise e


# ── Dependencies ────────────────────────────────────────────────────────────────


async def get_problem_dao(session: AsyncSession = Depends(get_db)) -> ProblemDAO:
    return ProblemDAO(session)


async def get_contest_problem_dao(
    session: AsyncSession = Depends(get_db),
) -> ContestProblemDAO:
    return ContestProblemDAO(session)


async def get_builtin_problem_dao(
    session: AsyncSession = Depends(get_db),
) -> BuiltinProblemDAO:
    return BuiltinProblemDAO(session)
