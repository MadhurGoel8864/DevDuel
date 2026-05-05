"""Problem Service Layer"""

import logging
from typing import Any

from fastapi import Depends

from app.api.common.text import slugify
from app.api.problems.dao.problems import (
    BuiltinProblemDAO,
    ContestProblemDAO,
    CustomProblemDAO,
    get_builtin_problem_dao,
    get_contest_problem_dao,
    get_custom_problem_dao,
)
from app.api.problems.schemas.problems import (
    BuiltinProblemCreateData,
    BuiltinProblemUpdateData,
    CustomProblemCreateData,
    CustomProblemUpdateData,
    ImportProblemData,
)
from app.core.enums import Difficulty
from app.core.exceptions.contests import ContestNotFoundException
from app.core.exceptions.problems import (
    BuiltinProblemNotFoundException,
    BuiltinProblemSlugConflictException,
    ContestProblemNotFoundException,
    CustomProblemAccessDeniedException,
    CustomProblemHasContestReferencesException,
    CustomProblemNotFoundException,
    CustomProblemSlugConflictException,
    InvalidProblemOrderException,
    NotContestOrganizerException,
    ProblemAlreadyInContestException,
)
from app.database.models.contests import Contest
from app.database.models.problems import (
    BuiltinProblem,
    ContestProblem,
    CustomProblem,
)

logger = logging.getLogger(__name__)


class BuiltinProblemService:
    """Business logic for built-in problems (browse + CRUD)."""

    SLUG_RETRY_LIMIT = 5

    def __init__(self, builtin_problem_dao: BuiltinProblemDAO):
        self._builtin_dao = builtin_problem_dao

    async def _generate_unique_slug(self, title: str) -> str:
        """Generate a globally-unique slug from a title.

        Tries the bare slug first; on conflict appends -2, -3 … up to SLUG_RETRY_LIMIT.
        """
        base = slugify(title)
        candidate = base
        for attempt in range(1, self.SLUG_RETRY_LIMIT + 1):
            if attempt > 1:
                candidate = f"{base}-{attempt}"
            existing = await self._builtin_dao.get_by_slug(candidate)
            if existing is None:
                return candidate
        raise BuiltinProblemSlugConflictException(slug=base)

    async def create(self, data: BuiltinProblemCreateData) -> BuiltinProblem:
        slug = await self._generate_unique_slug(data.title)
        sample_io = [item.model_dump() for item in data.sample_io]
        problem = await self._builtin_dao.create(
            title=data.title,
            slug=slug,
            description=data.description,
            input_format=data.input_format,
            output_format=data.output_format,
            constraints=data.constraints,
            sample_io=sample_io,
            difficulty=data.difficulty,
            points=data.points,
            base_price=data.base_price,
            time_limit_ms=data.time_limit_ms,
            memory_limit_mb=data.memory_limit_mb,
        )
        logger.info(f"Builtin problem created: id={problem.id} slug={slug}")
        return problem

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
        """Raise BuiltinProblemNotFoundException if not found or inactive."""
        problem = await self._builtin_dao.get_by_id(problem_id)
        if not problem or not problem.is_active:
            raise BuiltinProblemNotFoundException(builtin_problem_id=problem_id)
        return problem

    async def update(
        self, problem_id: str, data: BuiltinProblemUpdateData
    ) -> BuiltinProblem:
        problem = await self._builtin_dao.get_by_id(problem_id)
        if not problem:
            raise BuiltinProblemNotFoundException(builtin_problem_id=problem_id)

        update_fields: dict[str, Any] = {}
        if data.title is not None and data.title != problem.title:
            update_fields["title"] = data.title
            update_fields["slug"] = await self._generate_unique_slug(data.title)

        for field in (
            "description",
            "input_format",
            "output_format",
            "constraints",
            "difficulty",
            "points",
            "base_price",
            "time_limit_ms",
            "memory_limit_mb",
        ):
            value = getattr(data, field)
            if value is not None:
                update_fields[field] = value

        if data.sample_io is not None:
            update_fields["sample_io"] = [
                item.model_dump() for item in data.sample_io
            ]

        updated = await self._builtin_dao.update(problem, **update_fields)
        logger.info(
            f"Builtin problem updated: id={updated.id} fields={list(update_fields.keys())}"
        )
        return updated

    async def delete(self, problem_id: str) -> None:
        problem = await self._builtin_dao.get_by_id(problem_id)
        if not problem:
            raise BuiltinProblemNotFoundException(builtin_problem_id=problem_id)
        await self._builtin_dao.delete(problem)
        logger.info(f"Builtin problem deleted: id={problem_id}")

    async def set_test_cases_url(
        self, problem: BuiltinProblem, url: str
    ) -> BuiltinProblem:
        return await self._builtin_dao.set_test_cases_url(problem, url)


class CustomProblemService:
    """Business logic for admin-authored problems."""

    SLUG_RETRY_LIMIT = 5

    def __init__(self, custom_problem_dao: CustomProblemDAO):
        self._dao = custom_problem_dao

    async def _generate_unique_slug(self, owner_id: str, title: str) -> str:
        """Generate an owner-scoped unique slug from a title.

        Tries the bare slug first; on conflict, retries with ``-2``, ``-3`` …
        suffixes up to SLUG_RETRY_LIMIT total attempts before giving up.
        """
        base = slugify(title)
        candidate = base
        for attempt in range(1, self.SLUG_RETRY_LIMIT + 1):
            if attempt > 1:
                candidate = f"{base}-{attempt}"
            existing = await self._dao.get_by_owner_and_slug(owner_id, candidate)
            if existing is None:
                return candidate
        raise CustomProblemSlugConflictException(slug=base)

    async def create(
        self, user_id: str, data: CustomProblemCreateData
    ) -> CustomProblem:
        slug = await self._generate_unique_slug(user_id, data.title)
        sample_io = [item.model_dump() for item in data.sample_io]
        problem = await self._dao.create(
            created_by=user_id,
            title=data.title,
            slug=slug,
            description=data.description,
            input_format=data.input_format,
            output_format=data.output_format,
            constraints=data.constraints,
            sample_io=sample_io,
            difficulty=data.difficulty,
            points=data.points,
            base_price=data.base_price,
            time_limit_ms=data.time_limit_ms,
            memory_limit_mb=data.memory_limit_mb,
        )
        logger.info(
            f"Custom problem created: id={problem.id} slug={slug} owner={user_id}"
        )
        return problem

    async def list_mine(self, user_id: str) -> list[CustomProblem]:
        return await self._dao.list_by_owner(user_id)

    async def get_owned(
        self, user_id: str, custom_problem_id: str
    ) -> CustomProblem:
        problem = await self._dao.get_by_id(custom_problem_id)
        if problem is None:
            raise CustomProblemNotFoundException(custom_problem_id=custom_problem_id)
        if problem.created_by != user_id:
            raise CustomProblemAccessDeniedException(
                custom_problem_id=custom_problem_id
            )
        return problem

    async def update(
        self,
        user_id: str,
        custom_problem_id: str,
        data: CustomProblemUpdateData,
    ) -> CustomProblem:
        problem = await self.get_owned(user_id, custom_problem_id)

        update_fields: dict[str, Any] = {}
        # Re-slugify only if the title actually changed.
        if data.title is not None and data.title != problem.title:
            update_fields["title"] = data.title
            update_fields["slug"] = await self._generate_unique_slug(
                user_id, data.title
            )

        for field in (
            "description",
            "input_format",
            "output_format",
            "constraints",
            "difficulty",
            "points",
            "base_price",
            "time_limit_ms",
            "memory_limit_mb",
        ):
            value = getattr(data, field)
            if value is not None:
                update_fields[field] = value

        if data.sample_io is not None:
            update_fields["sample_io"] = [
                item.model_dump() for item in data.sample_io
            ]

        updated = await self._dao.update(problem, **update_fields)
        logger.info(
            f"Custom problem updated: id={updated.id} owner={user_id} "
            f"fields={list(update_fields.keys())}"
        )
        return updated

    async def delete(self, user_id: str, custom_problem_id: str) -> None:
        problem = await self.get_owned(user_id, custom_problem_id)
        ref_count = await self._dao.count_contest_references(custom_problem_id)
        if ref_count > 0:
            contest_ids = await self._dao.list_contest_ids_using(custom_problem_id)
            raise CustomProblemHasContestReferencesException(contest_ids=contest_ids)
        await self._dao.delete(problem)
        logger.info(
            f"Custom problem deleted: id={custom_problem_id} owner={user_id}"
        )

    async def set_test_cases_url(
        self, problem: CustomProblem, url: str
    ) -> CustomProblem:
        return await self._dao.set_test_cases_url(problem, url)


class ContestProblemService:
    """Business logic for managing contest problems."""

    def __init__(
        self,
        builtin_problem_dao: BuiltinProblemDAO,
        custom_problem_dao: CustomProblemDAO,
        contest_problem_dao: ContestProblemDAO,
    ):
        self._builtin_dao = builtin_problem_dao
        self._custom_dao = custom_problem_dao
        self._cp_dao = contest_problem_dao

    async def _get_contest_or_404(self, contest_id: str) -> Contest:
        contest = await self._cp_dao.get_contest(contest_id)
        if not contest:
            raise ContestNotFoundException(contest_id=contest_id)
        return contest

    async def _assert_organizer(
        self, contest: Contest, requesting_user_id: str
    ) -> None:
        if contest.created_by != requesting_user_id:
            raise NotContestOrganizerException(
                message="Only the contest organizer can perform this action"
            )

    async def _resolve_problem_order(
        self, contest_id: str, requested_order: int | None
    ) -> int:
        if requested_order is None:
            max_order = await self._cp_dao.get_max_order(contest_id)
            return max_order + 1
        if requested_order < 1:
            raise InvalidProblemOrderException(
                message="problem_order must be >= 1"
            )
        order_conflict = await self._cp_dao.get_by_contest_and_order(
            contest_id=contest_id, problem_order=requested_order
        )
        if order_conflict:
            raise InvalidProblemOrderException(
                message=f"problem_order {requested_order} is already taken in this contest"
            )
        return requested_order

    async def import_problem_to_contest(
        self,
        contest_id: str,
        requesting_user_id: str,
        data: ImportProblemData,
    ) -> ContestProblem:
        """Import either a built-in or a custom problem into a contest.

        For custom problems, the requesting user must own the problem.
        Contest authorization (must be the contest creator) applies in both cases.
        """
        contest = await self._get_contest_or_404(contest_id)
        await self._assert_organizer(contest, requesting_user_id)

        if data.builtin_problem_id is not None:
            builtin = await self._builtin_dao.get_by_id(data.builtin_problem_id)
            if not builtin or not builtin.is_active:
                raise BuiltinProblemNotFoundException(
                    builtin_problem_id=data.builtin_problem_id
                )
            existing = await self._cp_dao.get_by_contest_and_builtin(
                contest_id=contest_id,
                builtin_problem_id=data.builtin_problem_id,
            )
            if existing:
                raise ProblemAlreadyInContestException(
                    problem_id=data.builtin_problem_id, contest_id=contest_id
                )
            problem_order = await self._resolve_problem_order(
                contest_id, data.problem_order
            )
            cp = await self._cp_dao.add_builtin(
                contest_id=contest_id,
                builtin_problem_id=data.builtin_problem_id,
                problem_order=problem_order,
                difficulty=builtin.difficulty,
                points=builtin.points,
                base_price=builtin.base_price,
                time_limit_ms=builtin.time_limit_ms,
                memory_limit_mb=builtin.memory_limit_mb,
            )
            logger.info(
                f"Builtin problem {data.builtin_problem_id} imported into "
                f"contest {contest_id} at order {problem_order} by {requesting_user_id}"
            )
            return cp

        # Custom problem path
        assert data.custom_problem_id is not None  # validator guarantees this
        custom = await self._custom_dao.get_by_id(data.custom_problem_id)
        if custom is None or not custom.is_active:
            raise CustomProblemNotFoundException(
                custom_problem_id=data.custom_problem_id
            )
        # Anti-leak: only the owner can import their custom problem.
        if custom.created_by != requesting_user_id:
            raise CustomProblemAccessDeniedException(
                custom_problem_id=data.custom_problem_id
            )
        existing = await self._cp_dao.get_by_contest_and_custom(
            contest_id=contest_id,
            custom_problem_id=data.custom_problem_id,
        )
        if existing:
            raise ProblemAlreadyInContestException(
                problem_id=data.custom_problem_id, contest_id=contest_id
            )
        problem_order = await self._resolve_problem_order(
            contest_id, data.problem_order
        )
        cp = await self._cp_dao.add_custom(
            contest_id=contest_id,
            custom_problem_id=data.custom_problem_id,
            problem_order=problem_order,
            difficulty=custom.difficulty,
            points=custom.points,
            base_price=custom.base_price,
            time_limit_ms=custom.time_limit_ms,
            memory_limit_mb=custom.memory_limit_mb,
        )
        logger.info(
            f"Custom problem {data.custom_problem_id} imported into "
            f"contest {contest_id} at order {problem_order} by {requesting_user_id}"
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
        """Update contest-specific overrides for a problem."""
        contest = await self._get_contest_or_404(contest_id)
        await self._assert_organizer(contest, requesting_user_id)

        cp = await self._cp_dao.get_by_id(contest_problem_id)
        if not cp or cp.contest_id != contest_id or not cp.is_active:
            raise ContestProblemNotFoundException(
                contest_problem_id=contest_problem_id
            )

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


async def get_custom_problem_service(
    custom_problem_dao: CustomProblemDAO = Depends(get_custom_problem_dao),
) -> CustomProblemService:
    return CustomProblemService(custom_problem_dao=custom_problem_dao)


async def get_contest_problem_service(
    builtin_problem_dao: BuiltinProblemDAO = Depends(get_builtin_problem_dao),
    custom_problem_dao: CustomProblemDAO = Depends(get_custom_problem_dao),
    contest_problem_dao: ContestProblemDAO = Depends(get_contest_problem_dao),
) -> ContestProblemService:
    return ContestProblemService(
        builtin_problem_dao=builtin_problem_dao,
        custom_problem_dao=custom_problem_dao,
        contest_problem_dao=contest_problem_dao,
    )

# Used by the test-cases handlers to mutate CustomProblem.test_cases_url
__all__ = [
    "BuiltinProblemService",
    "CustomProblemService",
    "ContestProblemService",
    "get_builtin_problem_service",
    "get_custom_problem_service",
    "get_contest_problem_service",
]
