"""Problem Service Layer"""

import logging
import re

from fastapi import Depends

from app.api.problems.dao.problems import (
    ContestProblemDAO,
    ProblemDAO,
    get_contest_problem_dao,
    get_problem_dao,
)
from app.core.enums import Difficulty
from app.core.exceptions.common import BadRequestException
from app.core.exceptions.contests import ContestNotFoundException
from app.core.exceptions.problems import (
    InvalidProblemOrderException,
    ProblemAlreadyInContestException,
    ProblemNotFoundException,
)
from app.database.models.problems import ContestProblem, Problem

logger = logging.getLogger(__name__)


def _generate_slug(title: str) -> str:
    """Convert a title to a URL-safe slug.

    Lowercases the title, strips leading/trailing whitespace, and replaces
    runs of whitespace / non-alphanumeric characters with hyphens.
    """
    slug = title.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


class ProblemService:
    """Business logic for Problem operations."""

    def __init__(self, problem_dao: ProblemDAO):
        self._problem_dao = problem_dao

    async def _unique_slug(self, base_slug: str) -> str:
        """Return a slug that doesn't already exist in the DB.

        If ``base_slug`` is taken, try ``base_slug-2``, ``base_slug-3``, …
        """
        candidate = base_slug
        counter = 2
        while await self._problem_dao.slug_exists(candidate):
            candidate = f"{base_slug}-{counter}"
            counter += 1
        return candidate

    async def create_problem(
        self,
        title: str,
        description: str,
        difficulty: Difficulty,
        points: int,
        base_price: int,
        created_by: str,
        time_limit_ms: int = 2000,
        memory_limit_mb: int = 256,
    ) -> Problem:
        """Create a new problem. Slug is auto-generated from the title."""
        base_slug = _generate_slug(title)
        slug = await self._unique_slug(base_slug)
        problem = await self._problem_dao.create(
            title=title,
            slug=slug,
            description=description,
            difficulty=difficulty,
            points=points,
            base_price=base_price,
            created_by=created_by,
            time_limit_ms=time_limit_ms,
            memory_limit_mb=memory_limit_mb,
        )
        logger.info(f"Problem '{title}' created with slug '{slug}' by {created_by}")
        return problem

    async def get_problem_by_id(self, problem_id: str) -> Problem:
        """Raise ProblemNotFoundException if not found."""
        problem = await self._problem_dao.get_by_id(problem_id)
        if not problem:
            raise ProblemNotFoundException(problem_id=problem_id)
        return problem

    async def get_problem_by_slug(self, slug: str) -> Problem:
        """Raise ProblemNotFoundException if not found."""
        problem = await self._problem_dao.get_by_slug(slug)
        if not problem:
            raise ProblemNotFoundException(
                message=f"Problem with slug '{slug}' not found"
            )
        return problem

    async def list_problems(
        self,
        difficulty: Difficulty | None = None,
        search: str | None = None,
        created_by: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[Problem]:
        return await self._problem_dao.list_all(
            difficulty=difficulty,
            search=search,
            created_by=created_by,
            page=page,
            limit=limit,
        )

    async def update_problem(
        self,
        problem_id: str,
        requesting_user_id: str,
        **fields,
    ) -> Problem:
        """Update problem fields. Only the creator may update.

        Raises:
            ProblemNotFoundException: If the problem does not exist.
            BadRequestException: If the requester is not the creator.
        """
        problem = await self.get_problem_by_id(problem_id)
        if problem.created_by != requesting_user_id:
            raise BadRequestException(
                message="Only the problem creator can update this problem"
            )
        updated = await self._problem_dao.update(problem, **fields)
        logger.info(f"Problem {problem_id} updated by {requesting_user_id}")
        return updated

    async def soft_delete_problem(
        self, problem_id: str, requesting_user_id: str
    ) -> Problem:
        """Soft-delete a problem (is_active=False). Only the creator may do this.

        Raises:
            ProblemNotFoundException: If the problem does not exist.
            BadRequestException: If the requester is not the creator.
        """
        problem = await self.get_problem_by_id(problem_id)
        if problem.created_by != requesting_user_id:
            raise BadRequestException(
                message="Only the problem creator can delete this problem"
            )
        deleted = await self._problem_dao.soft_delete(problem)
        logger.info(f"Problem {problem_id} soft-deleted by {requesting_user_id}")
        return deleted


class ContestProblemService:
    """Business logic for attaching Problems to Contests."""

    def __init__(
        self,
        problem_dao: ProblemDAO,
        contest_problem_dao: ContestProblemDAO,
    ):
        self._problem_dao = problem_dao
        self._cp_dao = contest_problem_dao

    async def _assert_contest_exists(self, contest_id: str) -> None:
        """Raise ContestNotFoundException if the contest does not exist."""
        if not await self._cp_dao.contest_exists(contest_id):
            raise ContestNotFoundException(contest_id=contest_id)

    async def add_problem_to_contest(
        self,
        contest_id: str,
        problem_id: str,
        problem_order: int,
        requesting_user_id: str,
    ) -> ContestProblem:
        """Attach a problem to a contest in a specific bidding order.

        Validates:
            * contest exists
            * problem exists and is active
            * problem not already in contest
            * problem_order >= 1
            * order unique within contest

        Raises:
            ContestNotFoundException, ProblemNotFoundException,
            ProblemAlreadyInContestException, InvalidProblemOrderException.
        """
        await self._assert_contest_exists(contest_id)

        problem = await self._problem_dao.get_by_id(problem_id)
        if not problem or not problem.is_active:
            raise ProblemNotFoundException(problem_id=problem_id)

        if problem_order < 1:
            raise InvalidProblemOrderException(message="problem_order must be >= 1")

        existing = await self._cp_dao.get_by_contest_and_problem(
            contest_id=contest_id, problem_id=problem_id
        )
        if existing:
            raise ProblemAlreadyInContestException(
                problem_id=problem_id, contest_id=contest_id
            )

        order_conflict = await self._cp_dao.get_by_contest_and_order(
            contest_id=contest_id, problem_order=problem_order
        )
        if order_conflict:
            raise InvalidProblemOrderException(
                message=f"problem_order {problem_order} is already taken in this contest"
            )

        cp = await self._cp_dao.add(
            contest_id=contest_id,
            problem_id=problem_id,
            problem_order=problem_order,
        )
        logger.info(
            f"Problem {problem_id} added to contest {contest_id} "
            f"at order {problem_order} by {requesting_user_id}"
        )
        return cp

    async def list_contest_problems(self, contest_id: str) -> list[ContestProblem]:
        """Return active contest-problems sorted by problem_order."""
        await self._assert_contest_exists(contest_id)
        return await self._cp_dao.list_by_contest(contest_id)

    async def get_contest_problem(
        self, contest_id: str, contest_problem_id: str
    ) -> ContestProblem:
        """Fetch a specific ContestProblem by its own ID.

        Raises ProblemNotFoundException if not found or not in the contest.
        """
        cp = await self._cp_dao.get_by_id(contest_problem_id)
        if not cp or cp.contest_id != contest_id:
            raise ProblemNotFoundException(
                message=f"ContestProblem '{contest_problem_id}' not found in contest '{contest_id}'"
            )
        return cp

    async def remove_problem_from_contest(
        self,
        contest_id: str,
        contest_problem_id: str,
        requesting_user_id: str,
    ) -> ContestProblem:
        """Soft-delete a ContestProblem (is_active=False).

        Raises ProblemNotFoundException if not found.
        """
        cp = await self.get_contest_problem(contest_id, contest_problem_id)
        removed = await self._cp_dao.soft_delete(cp)
        logger.info(
            f"ContestProblem {contest_problem_id} removed from contest {contest_id} "
            f"by {requesting_user_id}"
        )
        return removed


# ── Dependencies ────────────────────────────────────────────────────────────────


async def get_problem_service(
    problem_dao: ProblemDAO = Depends(get_problem_dao),
) -> ProblemService:
    return ProblemService(problem_dao=problem_dao)


async def get_contest_problem_service(
    problem_dao: ProblemDAO = Depends(get_problem_dao),
    contest_problem_dao: ContestProblemDAO = Depends(get_contest_problem_dao),
) -> ContestProblemService:
    return ContestProblemService(
        problem_dao=problem_dao,
        contest_problem_dao=contest_problem_dao,
    )
