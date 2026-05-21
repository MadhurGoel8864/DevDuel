"""Problem Service Layer"""

import asyncio
import base64
import logging
from datetime import datetime
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
from app.core.enums import Difficulty, ValidationStatus
from app.core.exceptions.contests import ContestNotFoundException
from app.core.exceptions.problems import (
    BuiltinProblemNotFoundException,
    BuiltinProblemSlugConflictException,
    ContestProblemNotFoundException,
    CustomProblemAccessDeniedException,
    CustomProblemHasContestReferencesException,
    CustomProblemNotFoundException,
    CustomProblemNotValidatedException,
    CustomProblemSlugConflictException,
    InvalidLanguageException,
    InvalidProblemOrderException,
    Judge0TimeoutException,
    NotContestOrganizerException,
    ProblemAlreadyInContestException,
    TestCasesNotFoundException,
)
from app.database.models.contests import Contest
from app.database.models.problems import (
    BuiltinProblem,
    ContestProblem,
    CustomProblem,
)
from app.services.judge0.client import Judge0Client, Judge0Error, Judge0TimeoutError
from app.services.judge0.constants import JUDGE0_TO_VERDICT, Judge0StatusId, SUPPORTED_LANGUAGES
from app.services.judge0.schemas import Judge0SubmissionRequest
from app.services.storage import storage_service
from app.services.storage.gcs import StorageError

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
        problem = await self._builtin_dao.create(
            title=data.title,
            slug=slug,
            description=data.description,
            input_format=data.input_format,
            output_format=data.output_format,
            constraints=data.constraints,
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

    async def probe(
        self,
        problem_id: str,
        language: str,
        source_code: str,
        judge0: Judge0Client,
    ) -> dict:
        """Run any solution against a built-in problem's test cases without any DB writes.

        Use this to calibrate time/memory limits — test optimised and brute-force
        solutions to confirm the right ones pass and slow ones TLE.
        """
        problem = await self._builtin_dao.get_by_id(problem_id)
        if not problem or not problem.is_active:
            raise BuiltinProblemNotFoundException(builtin_problem_id=problem_id)

        if not problem.test_cases_url:
            raise TestCasesNotFoundException(problem_id=problem_id)

        try:
            test_cases = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: storage_service.download_test_cases_from_url(
                    problem.test_cases_url
                ),
            )
        except StorageError:
            raise TestCasesNotFoundException(problem_id=problem_id)

        if not test_cases:
            raise TestCasesNotFoundException(problem_id=problem_id)

        language_lower = language.lower()
        if language_lower not in SUPPORTED_LANGUAGES:
            raise InvalidLanguageException(
                language=language,
                supported=list(SUPPORTED_LANGUAGES.keys()),
            )
        language_id = SUPPORTED_LANGUAGES[language_lower]

        source_b64 = base64.b64encode(source_code.encode()).decode()
        cpu_time_limit = problem.time_limit_ms / 1000.0
        wall_time_limit = cpu_time_limit * 3
        memory_limit = problem.memory_limit_mb * 1024.0

        judge0_submissions = []
        for tc in test_cases:
            stdin_b64 = base64.b64encode(tc["input"].encode()).decode()
            expected_b64 = base64.b64encode(tc["expected_output"].encode()).decode()
            judge0_submissions.append(
                Judge0SubmissionRequest(
                    source_code=source_b64,
                    language_id=language_id,
                    stdin=stdin_b64,
                    expected_output=expected_b64,
                    cpu_time_limit=cpu_time_limit,
                    wall_time_limit=wall_time_limit,
                    memory_limit=memory_limit,
                )
            )

        logger.info(
            f"[builtin_probe] Submitting {len(judge0_submissions)} test cases to Judge0 "
            f"for builtin problem {problem_id}"
        )
        try:
            tokens = await judge0.create_batch_submissions(judge0_submissions)
        except Judge0Error as e:
            logger.error(f"[builtin_probe] Judge0 batch submit failed: {e}")
            raise

        try:
            results = await judge0.poll_batch_fail_fast(tokens)
        except Judge0TimeoutError as e:
            logger.error(f"[builtin_probe] Judge0 polling failed: {e}")
            raise Judge0TimeoutException() from e
        except Judge0Error as e:
            logger.error(f"[builtin_probe] Judge0 polling failed: {e}")
            raise

        passed = 0
        test_result_list = []
        for idx, (tc, result) in enumerate(zip(test_cases, results)):
            if result.status.id <= Judge0StatusId.PROCESSING:
                continue

            verdict_str = JUDGE0_TO_VERDICT.get(result.status.id, "INTERNAL_ERROR")
            memory_kb = int(result.memory) if result.memory else None
            if verdict_str == "RUNTIME_ERROR" and memory_kb is not None and memory_kb >= memory_limit:
                verdict_str = "MEMORY_LIMIT_EXCEEDED"
            tc_passed = result.status.id == Judge0StatusId.ACCEPTED
            if tc_passed:
                passed += 1

            test_result_list.append(
                {
                    "index": idx,
                    "is_sample": bool(tc.get("is_sample", False)),
                    "passed": tc_passed,
                    "verdict": verdict_str,
                    "input": tc["input"],
                    "expected_output": tc["expected_output"],
                    "actual_output": _b64_decode(result.stdout),
                    "time_ms": int(result.time * 1000) if result.time else None,
                    "memory_kb": memory_kb,
                    "stderr": _b64_decode(result.stderr),
                    "compile_output": _b64_decode(result.compile_output),
                }
            )

        logger.info(
            f"[builtin_probe] Builtin problem {problem_id}: "
            f"passed={passed}/{len(test_cases)}"
        )

        return {
            "problem_id": problem_id,
            "passed": passed,
            "total": len(test_cases),
            "test_results": test_result_list,
        }


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
        problem = await self._dao.create(
            created_by=user_id,
            title=data.title,
            slug=slug,
            description=data.description,
            input_format=data.input_format,
            output_format=data.output_format,
            constraints=data.constraints,
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

    async def validate(
        self,
        user_id: str,
        custom_problem_id: str,
        language: str,
        source_code: str,
        judge0: Judge0Client,
    ) -> dict:
        """Run a reference solution against the problem's test cases via Judge0.

        Updates validation_status to VALID if every test case passes, INVALID otherwise.
        Returns per-test-case results for the organizer to review.
        """
        problem = await self.get_owned(user_id, custom_problem_id)

        if not problem.test_cases_url:
            raise TestCasesNotFoundException(problem_id=custom_problem_id)

        try:
            test_cases = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: storage_service.download_test_cases_from_url(
                    problem.test_cases_url
                ),
            )
        except StorageError:
            raise TestCasesNotFoundException(problem_id=custom_problem_id)

        if not test_cases:
            raise TestCasesNotFoundException(problem_id=custom_problem_id)

        language_lower = language.lower()
        if language_lower not in SUPPORTED_LANGUAGES:
            raise InvalidLanguageException(
                language=language,
                supported=list(SUPPORTED_LANGUAGES.keys()),
            )
        language_id = SUPPORTED_LANGUAGES[language_lower]

        source_b64 = base64.b64encode(source_code.encode()).decode()
        cpu_time_limit = problem.time_limit_ms / 1000.0
        wall_time_limit = cpu_time_limit * 3
        memory_limit = problem.memory_limit_mb * 1024.0

        judge0_submissions = []
        for tc in test_cases:
            stdin_b64 = base64.b64encode(tc["input"].encode()).decode()
            expected_b64 = base64.b64encode(tc["expected_output"].encode()).decode()
            judge0_submissions.append(
                Judge0SubmissionRequest(
                    source_code=source_b64,
                    language_id=language_id,
                    stdin=stdin_b64,
                    expected_output=expected_b64,
                    cpu_time_limit=cpu_time_limit,
                    wall_time_limit=wall_time_limit,
                    memory_limit=memory_limit,
                )
            )

        logger.info(
            f"[validate] Submitting {len(judge0_submissions)} test cases to Judge0 "
            f"for custom problem {custom_problem_id}"
        )
        try:
            tokens = await judge0.create_batch_submissions(judge0_submissions)
        except Judge0Error as e:
            logger.error(f"[validate] Judge0 batch submit failed: {e}")
            raise

        try:
            results = await judge0.poll_batch_fail_fast(tokens)
        except Judge0TimeoutError as e:
            logger.error(f"[validate] Judge0 polling failed: {e}")
            raise Judge0TimeoutException() from e
        except Judge0Error as e:
            logger.error(f"[validate] Judge0 polling failed: {e}")
            raise

        passed = 0
        test_result_list = []
        for idx, (tc, result) in enumerate(zip(test_cases, results)):
            if result.status.id <= Judge0StatusId.PROCESSING:
                continue

            verdict_str = JUDGE0_TO_VERDICT.get(result.status.id, "INTERNAL_ERROR")
            memory_kb = int(result.memory) if result.memory else None
            if verdict_str == "RUNTIME_ERROR" and memory_kb is not None and memory_kb >= memory_limit:
                verdict_str = "MEMORY_LIMIT_EXCEEDED"
            tc_passed = result.status.id == Judge0StatusId.ACCEPTED
            if tc_passed:
                passed += 1

            test_result_list.append(
                {
                    "index": idx,
                    "is_sample": bool(tc.get("is_sample", False)),
                    "passed": tc_passed,
                    "verdict": verdict_str,
                    "input": tc["input"],
                    "expected_output": tc["expected_output"],
                    "actual_output": _b64_decode(result.stdout),
                    "time_ms": int(result.time * 1000) if result.time else None,
                    "memory_kb": memory_kb,
                    "stderr": _b64_decode(result.stderr),
                    "compile_output": _b64_decode(result.compile_output),
                }
            )

        new_status = (
            ValidationStatus.VALID if passed == len(test_cases) else ValidationStatus.INVALID
        )
        await self._dao.set_validation_status(
            problem, new_status, validated_at=datetime.now()
        )
        logger.info(
            f"[validate] Custom problem {custom_problem_id}: "
            f"status={new_status.value}, passed={passed}/{len(test_cases)}"
        )

        return {
            "problem_id": custom_problem_id,
            "validation_status": new_status.value,
            "passed": passed,
            "total": len(test_cases),
            "test_results": test_result_list,
        }

    async def probe(
        self,
        user_id: str,
        custom_problem_id: str,
        language: str,
        source_code: str,
        judge0: Judge0Client,
    ) -> dict:
        """Run any solution against the problem's test cases without changing validation_status.

        Identical execution pipeline to validate(), but the DB is never touched.
        Use this to calibrate time/memory limits by testing both optimised and
        brute-force solutions before committing to a reference run.
        """
        problem = await self.get_owned(user_id, custom_problem_id)

        if not problem.test_cases_url:
            raise TestCasesNotFoundException(problem_id=custom_problem_id)

        try:
            test_cases = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: storage_service.download_test_cases_from_url(
                    problem.test_cases_url
                ),
            )
        except StorageError:
            raise TestCasesNotFoundException(problem_id=custom_problem_id)

        if not test_cases:
            raise TestCasesNotFoundException(problem_id=custom_problem_id)

        language_lower = language.lower()
        if language_lower not in SUPPORTED_LANGUAGES:
            raise InvalidLanguageException(
                language=language,
                supported=list(SUPPORTED_LANGUAGES.keys()),
            )
        language_id = SUPPORTED_LANGUAGES[language_lower]

        source_b64 = base64.b64encode(source_code.encode()).decode()
        cpu_time_limit = problem.time_limit_ms / 1000.0
        wall_time_limit = cpu_time_limit * 3
        memory_limit = problem.memory_limit_mb * 1024.0

        judge0_submissions = []
        for tc in test_cases:
            stdin_b64 = base64.b64encode(tc["input"].encode()).decode()
            expected_b64 = base64.b64encode(tc["expected_output"].encode()).decode()
            judge0_submissions.append(
                Judge0SubmissionRequest(
                    source_code=source_b64,
                    language_id=language_id,
                    stdin=stdin_b64,
                    expected_output=expected_b64,
                    cpu_time_limit=cpu_time_limit,
                    wall_time_limit=wall_time_limit,
                    memory_limit=memory_limit,
                )
            )

        logger.info(
            f"[probe] Submitting {len(judge0_submissions)} test cases to Judge0 "
            f"for custom problem {custom_problem_id}"
        )
        try:
            tokens = await judge0.create_batch_submissions(judge0_submissions)
        except Judge0Error as e:
            logger.error(f"[probe] Judge0 batch submit failed: {e}")
            raise

        try:
            results = await judge0.poll_batch_fail_fast(tokens)
        except Judge0TimeoutError as e:
            logger.error(f"[probe] Judge0 polling failed: {e}")
            raise Judge0TimeoutException() from e
        except Judge0Error as e:
            logger.error(f"[probe] Judge0 polling failed: {e}")
            raise

        passed = 0
        test_result_list = []
        for idx, (tc, result) in enumerate(zip(test_cases, results)):
            if result.status.id <= Judge0StatusId.PROCESSING:
                continue

            verdict_str = JUDGE0_TO_VERDICT.get(result.status.id, "INTERNAL_ERROR")
            memory_kb = int(result.memory) if result.memory else None
            if verdict_str == "RUNTIME_ERROR" and memory_kb is not None and memory_kb >= memory_limit:
                verdict_str = "MEMORY_LIMIT_EXCEEDED"
            tc_passed = result.status.id == Judge0StatusId.ACCEPTED
            if tc_passed:
                passed += 1

            test_result_list.append(
                {
                    "index": idx,
                    "is_sample": bool(tc.get("is_sample", False)),
                    "passed": tc_passed,
                    "verdict": verdict_str,
                    "input": tc["input"],
                    "expected_output": tc["expected_output"],
                    "actual_output": _b64_decode(result.stdout),
                    "time_ms": int(result.time * 1000) if result.time else None,
                    "memory_kb": memory_kb,
                    "stderr": _b64_decode(result.stderr),
                    "compile_output": _b64_decode(result.compile_output),
                }
            )

        logger.info(
            f"[probe] Custom problem {custom_problem_id}: "
            f"passed={passed}/{len(test_cases)} (validation_status unchanged)"
        )

        return {
            "problem_id": custom_problem_id,
            "passed": passed,
            "total": len(test_cases),
            "test_results": test_result_list,
        }


def _b64_decode(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return base64.b64decode(value).decode("utf-8", errors="replace")
    except Exception:
        return value


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
        if custom.validation_status != ValidationStatus.VALID:
            raise CustomProblemNotValidatedException(
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
