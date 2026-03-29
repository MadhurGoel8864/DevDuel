"""Problem Service Layer"""

import logging

from fastapi import Depends

from app.api.problems.dao.problems import (
    BuiltinProblemDAO,
    ContestProblemDAO,
    get_builtin_problem_dao,
    get_contest_problem_dao,
)
from app.core.enums import Difficulty
from app.core.exceptions.contests import ContestNotFoundException
from app.core.exceptions.problems import (
    BuiltinProblemNotFoundException,
    ContestProblemNotFoundException,
    InvalidProblemOrderException,
    NotContestOrganizerException,
    ProblemAlreadyInContestException,
)
from app.database.models.contests import Contest
from app.database.models.problems import BuiltinProblem, ContestProblem

logger = logging.getLogger(__name__)


class BuiltinProblemService:
    """Business logic for browsing built-in problems."""

    def __init__(self, builtin_problem_dao: BuiltinProblemDAO):
        self._builtin_dao = builtin_problem_dao

    async def list_builtin_problems(
        self,
        difficulty: Difficulty | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> tuple[list[BuiltinProblem], int]:
        """Return active built-in problems with optional filters and total count."""
        problems = await self._builtin_dao.list_all(
            difficulty=difficulty,
            search=search,
            page=page,
            limit=limit,
        )
        total = await self._builtin_dao.count(
            difficulty=difficulty,
            search=search,
        )
        return problems, total

    async def get_builtin_problem_by_id(
        self, problem_id: str
    ) -> BuiltinProblem:
        """Raise BuiltinProblemNotFoundException if not found."""
        problem = await self._builtin_dao.get_by_id(problem_id)
        if not problem or not problem.is_active:
            raise BuiltinProblemNotFoundException(builtin_problem_id=problem_id)
        return problem


class ContestProblemService:
    """Business logic for managing contest problems."""

    def __init__(
        self,
        builtin_problem_dao: BuiltinProblemDAO,
        contest_problem_dao: ContestProblemDAO,
    ):
        self._builtin_dao = builtin_problem_dao
        self._cp_dao = contest_problem_dao

    async def _get_contest_or_404(self, contest_id: str) -> Contest:
        """Raise ContestNotFoundException if the contest does not exist."""
        contest = await self._cp_dao.get_contest(contest_id)
        if not contest:
            raise ContestNotFoundException(contest_id=contest_id)
        return contest

    async def _assert_organizer(
        self, contest: Contest, requesting_user_id: str
    ) -> None:
        """Raise NotContestOrganizerException if not the contest creator."""
        if contest.created_by != requesting_user_id:
            raise NotContestOrganizerException(
                message="Only the contest organizer can perform this action"
            )

    async def import_builtin_problem_to_contest(
        self,
        builtin_problem_id: str,
        contest_id: str,
        requesting_user_id: str,
        problem_order: int | None = None,
    ) -> ContestProblem:
        """Import a built-in problem into a contest.

        Creates a contest_problems row referencing the builtin problem directly,
        copying default values for difficulty/points/base_price/time_limit/memory_limit.
        If problem_order is not provided, auto-assigns the next available order.
        """
        # 1. Validate contest and authorization
        contest = await self._get_contest_or_404(contest_id)
        await self._assert_organizer(contest, requesting_user_id)

        # 2. Validate builtin problem
        builtin = await self._builtin_dao.get_by_id(builtin_problem_id)
        if not builtin or not builtin.is_active:
            raise BuiltinProblemNotFoundException(
                builtin_problem_id=builtin_problem_id
            )

        # 3. Check duplicate
        existing = await self._cp_dao.get_by_contest_and_problem(
            contest_id=contest_id, problem_id=builtin_problem_id
        )
        if existing:
            raise ProblemAlreadyInContestException(
                problem_id=builtin_problem_id, contest_id=contest_id
            )

        # 4. Resolve problem_order: auto-assign if not provided
        if problem_order is None:
            max_order = await self._cp_dao.get_max_order(contest_id)
            problem_order = max_order + 1
        else:
            if problem_order < 1:
                raise InvalidProblemOrderException(
                    message="problem_order must be >= 1"
                )
            order_conflict = await self._cp_dao.get_by_contest_and_order(
                contest_id=contest_id, problem_order=problem_order
            )
            if order_conflict:
                raise InvalidProblemOrderException(
                    message=f"problem_order {problem_order} is already taken in this contest"
                )

        # 5. Create contest problem with defaults from builtin
        cp = await self._cp_dao.add(
            contest_id=contest_id,
            problem_id=builtin_problem_id,
            problem_order=problem_order,
            difficulty=builtin.difficulty,
            points=builtin.points,
            base_price=builtin.base_price,
            time_limit_ms=builtin.time_limit_ms,
            memory_limit_mb=builtin.memory_limit_mb,
            test_cases_url=builtin.test_cases_url,
        )
        logger.info(
            f"Builtin problem {builtin_problem_id} imported into contest {contest_id} "
            f"at order {problem_order} by {requesting_user_id}"
        )
        return cp

    async def list_contest_problems(
        self, contest_id: str
    ) -> list[ContestProblem]:
        """Return active contest-problems sorted by problem_order."""
        contest = await self._cp_dao.get_contest(contest_id)
        if not contest:
            raise ContestNotFoundException(contest_id=contest_id)
        return await self._cp_dao.list_by_contest(contest_id)

    async def remove_problem_from_contest(
        self,
        contest_id: str,
        contest_problem_id: str,
        requesting_user_id: str,
    ) -> ContestProblem:
        """Hard-delete a ContestProblem row."""
        contest = await self._get_contest_or_404(contest_id)
        await self._assert_organizer(contest, requesting_user_id)

        cp = await self._cp_dao.get_by_id(contest_problem_id)
        if not cp or cp.contest_id != contest_id:
            raise ContestProblemNotFoundException(
                contest_problem_id=contest_problem_id
            )

        await self._cp_dao.delete(cp)

        # Resequence remaining problems to close order gaps
        await self._cp_dao.resequence_orders(contest_id)

        logger.info(
            f"ContestProblem {contest_problem_id} deleted from contest {contest_id} "
            f"by {requesting_user_id}"
        )
        return cp

    async def update_contest_problem(
        self,
        contest_id: str,
        contest_problem_id: str,
        requesting_user_id: str,
        **fields,
    ) -> ContestProblem:
        """Update contest-specific overrides for a problem.

        Allowed fields: difficulty, points, base_price, time_limit_ms,
        memory_limit_mb, problem_order.
        """
        contest = await self._get_contest_or_404(contest_id)
        await self._assert_organizer(contest, requesting_user_id)

        cp = await self._cp_dao.get_by_id(contest_problem_id)
        if not cp or cp.contest_id != contest_id or not cp.is_active:
            raise ContestProblemNotFoundException(
                contest_problem_id=contest_problem_id
            )

        # If problem_order is being changed, check for conflicts
        new_order = fields.get("problem_order")
        if new_order is not None and new_order != cp.problem_order:
            order_conflict = await self._cp_dao.get_by_contest_and_order(
                contest_id=contest_id, problem_order=new_order
            )
            if order_conflict:
                raise InvalidProblemOrderException(
                    message=f"problem_order {new_order} is already taken in this contest"
                )

        updated = await self._cp_dao.update(cp, **fields)
        logger.info(
            f"ContestProblem {contest_problem_id} updated in contest {contest_id} "
            f"by {requesting_user_id}"
        )
        return updated


# ── Dependencies ────────────────────────────────────────────────────────────────


async def get_builtin_problem_service(
    builtin_problem_dao: BuiltinProblemDAO = Depends(get_builtin_problem_dao),
) -> BuiltinProblemService:
    return BuiltinProblemService(builtin_problem_dao=builtin_problem_dao)


async def get_contest_problem_service(
    builtin_problem_dao: BuiltinProblemDAO = Depends(get_builtin_problem_dao),
    contest_problem_dao: ContestProblemDAO = Depends(get_contest_problem_dao),
) -> ContestProblemService:
    return ContestProblemService(
        builtin_problem_dao=builtin_problem_dao,
        contest_problem_dao=contest_problem_dao,
    )
