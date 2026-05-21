"""Submissions Service Layer — core judging pipeline."""

import asyncio
import base64
import logging
from datetime import datetime

from fastapi import Depends

from app.api.contests.services.leaderboard_broadcast import broadcast_leaderboard
from app.api.submissions.dao.submissions import SubmissionDAO, get_submission_dao
from app.core.enums import (
    AssignmentStatus,
    ContestStatus,
    SubmissionVerdict,
    TeamRole,
)
from app.core.exceptions.base import AppException
from app.database.models.submissions import (
    Submission,
    SubmissionTestResult,
    TeamProblemSolution,
)
from app.services.judge0.client import Judge0Client, Judge0Error, Judge0TimeoutError
from app.services.judge0.constants import JUDGE0_TO_VERDICT, Judge0StatusId, SUPPORTED_LANGUAGES
from app.services.judge0.schemas import Judge0SubmissionRequest
from app.services.storage import storage_service
from app.services.storage.cache import get_cached_test_cases, set_cached_test_cases
from app.services.storage.gcs import StorageError

logger = logging.getLogger(__name__)


# ── Exceptions ────────────────────────────────────────────────────────────────


class SubmissionException(AppException):
    pass


class ContestNotActiveException(SubmissionException):
    def __init__(self):
        super().__init__(
            code="CONTEST_NOT_ACTIVE",
            message="Submissions are only allowed while the contest is ACTIVE",
            status_code=400,
        )


class NotCodingRoleException(SubmissionException):
    def __init__(self):
        super().__init__(
            code="NOT_CODING_ROLE",
            message="Only the team member with CODING role can submit code",
            status_code=403,
        )


class ProblemNotAssignedException(SubmissionException):
    def __init__(self):
        super().__init__(
            code="PROBLEM_NOT_ASSIGNED",
            message="Your team has not won this problem in the auction",
            status_code=403,
        )


class ProblemAlreadySolvedException(SubmissionException):
    def __init__(self):
        super().__init__(
            code="PROBLEM_ALREADY_SOLVED",
            message="This problem has already been solved by your team",
            status_code=400,
        )


class UnsupportedLanguageException(SubmissionException):
    def __init__(self, language: str):
        super().__init__(
            code="UNSUPPORTED_LANGUAGE",
            message=f"Language '{language}' is not supported. "
            f"Supported: {', '.join(SUPPORTED_LANGUAGES.keys())}",
            status_code=400,
        )


class NoTestCasesException(SubmissionException):
    def __init__(self):
        super().__init__(
            code="NO_TEST_CASES",
            message="This problem has no test cases configured",
            status_code=400,
        )


class NoSampleTestCasesException(SubmissionException):
    def __init__(self):
        super().__init__(
            code="NO_SAMPLE_TEST_CASES",
            message="This problem has no sample test cases to run against",
            status_code=400,
        )


class JudgeServiceException(SubmissionException):
    def __init__(self, detail: str = ""):
        super().__init__(
            code="JUDGE_SERVICE_ERROR",
            message=f"Code execution service error: {detail}" if detail else
            "Code execution service is unavailable",
            status_code=502,
        )


class SubmissionNotFoundException(SubmissionException):
    def __init__(self, submission_id: str = ""):
        super().__init__(
            code="SUBMISSION_NOT_FOUND",
            message=f"Submission '{submission_id}' not found" if submission_id else
            "Submission not found",
            status_code=404,
        )


class LatestSolutionNotFoundException(SubmissionException):
    def __init__(self):
        super().__init__(
            code="LATEST_SOLUTION_NOT_FOUND",
            message="No code has been submitted yet for this team and problem",
            status_code=404,
        )


class NotAllowedToViewCodeException(SubmissionException):
    def __init__(self):
        super().__init__(
            code="NOT_ALLOWED_TO_VIEW_CODE",
            message="Only team members or organizers can view this code",
            status_code=403,
        )


# ── Service ───────────────────────────────────────────────────────────────────


class SubmissionService:
    """Business logic for code submissions and Judge0 orchestration."""

    def __init__(self, dao: SubmissionDAO, judge0: Judge0Client):
        self._dao = dao
        self._judge0 = judge0

    async def submit_code(
        self,
        contest_id: str,
        contest_problem_id: str,
        team_id: str,
        user_id: str,
        language: str,
        source_code: str,
    ) -> tuple["Submission", list[dict], int, float]:
        """Phase 1 of the judging pipeline: validate → fetch test cases → submit to Judge0.

        Returns (submission, test_cases, points). The submission has verdict=PENDING.
        Polling and result processing happen in the ARQ background task.
        """
        logger.info(
            f"[submit] Starting: contest={contest_id}, problem={contest_problem_id}, "
            f"team={team_id}, user={user_id}, lang={language}, "
            f"code_len={len(source_code)} chars"
        )

        # ── 1. Validate contest is ACTIVE ─────────────────────────────────────
        contest = await self._dao.get_contest(contest_id)
        if not contest or contest.status != ContestStatus.ACTIVE:
            logger.warning(
                f"[submit] Contest not active: {contest_id}, "
                f"status={contest.status if contest else 'NOT_FOUND'}"
            )
            raise ContestNotActiveException()

        # ── 2. Validate user has CODING role in team ──────────────────────────
        member = await self._dao.get_team_member(team_id, user_id)
        if not member or member.role != TeamRole.CODING:
            logger.warning(
                f"[submit] User {user_id} not CODING role in team {team_id}, "
                f"role={member.role if member else 'NOT_MEMBER'}"
            )
            raise NotCodingRoleException()

        # ── 3. Validate assignment exists and is ASSIGNED ─────────────────────
        assignment = await self._dao.get_assignment(contest_problem_id, team_id)
        if not assignment:
            logger.warning(f"[submit] No assignment: problem={contest_problem_id}, team={team_id}")
            raise ProblemNotAssignedException()
        if assignment.status == AssignmentStatus.SOLVED:
            logger.warning(f"[submit] Already solved: assignment={assignment.id}")
            raise ProblemAlreadySolvedException()

        # ── 4. Validate language ──────────────────────────────────────────────
        language_lower = language.lower()
        if language_lower not in SUPPORTED_LANGUAGES:
            logger.warning(f"[submit] Unsupported language: '{language}'")
            raise UnsupportedLanguageException(language)
        language_id = SUPPORTED_LANGUAGES[language_lower]
        logger.debug(f"[submit] Language resolved: {language_lower} → id={language_id}")

        # ── 5. Fetch test cases from GCS (via the underlying problem) ──────────
        contest_problem = await self._dao.get_contest_problem(contest_problem_id)
        if not contest_problem:
            logger.warning(
                f"[submit] Contest problem not found: {contest_problem_id}"
            )
            raise NoTestCasesException()

        # Test cases live on the underlying problem (built-in or custom).
        # ``resolved_problem`` returns whichever side of the polymorphic
        # ContestProblem is populated.
        underlying_problem = contest_problem.resolved_problem
        if not underlying_problem or not underlying_problem.test_cases_url:
            logger.warning(
                f"[submit] No test cases URL on underlying problem for contest problem {contest_problem_id}"
            )
            raise NoTestCasesException()

        gcs_url = underlying_problem.test_cases_url
        logger.debug(f"[submit] Fetching test cases from: {gcs_url}")

        test_cases = await get_cached_test_cases(gcs_url)
        if test_cases is None:
            try:
                test_cases = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: storage_service.download_test_cases_from_url(gcs_url),
                )
            except StorageError as e:
                logger.error(f"[submit] GCS download failed: {e}")
                raise NoTestCasesException()
            await set_cached_test_cases(gcs_url, test_cases)
            logger.info(f"[submit] GCS cache miss — downloaded and cached {len(test_cases)} test cases")
        else:
            logger.info(f"[submit] GCS cache hit — {len(test_cases)} test cases")

        if not test_cases:
            logger.warning(f"[submit] Empty test cases for problem {contest_problem_id}")
            raise NoTestCasesException()

        # ── 6. Create Submission record (PENDING) ─────────────────────────────
        logger.debug(
            f"[submit] Problem limits: time={contest_problem.time_limit_ms}ms, "
            f"memory={contest_problem.memory_limit_mb}MB, points={contest_problem.points}"
        )
        submission = Submission(
            contest_id=contest_id,
            contest_problem_id=contest_problem_id,
            assignment_id=assignment.id,
            team_id=team_id,
            user_id=user_id,
            language=language_lower,
            language_id=language_id,
            source_code=source_code,
            verdict=SubmissionVerdict.PENDING,
            total_test_cases=len(test_cases),
        )
        submission = await self._dao.create_submission(submission)
        logger.info(f"[submit] Submission record created: id={submission.id}")

        # Persist as the team's latest code for this problem (overwrite-on-submit).
        # Failure here must not poison the judging pipeline — we log and continue.
        try:
            await self._dao.upsert_team_problem_solution(
                team_id=team_id,
                contest_problem_id=contest_problem_id,
                contest_id=contest_id,
                language=language_lower,
                source_code=source_code,
                last_submission_id=submission.id,
            )
        except Exception as e:
            logger.error(
                f"[submit] Failed to upsert TeamProblemSolution for submission "
                f"{submission.id}: {e}"
            )

        # ── 7. Build Judge0 batch request ─────────────────────────────────────
        source_b64 = base64.b64encode(source_code.encode()).decode()

        # Convert problem limits: ms→s, MB→KB
        cpu_time_limit = contest_problem.time_limit_ms / 1000.0
        wall_time_limit = cpu_time_limit * 3  # generous wall time
        memory_limit = contest_problem.memory_limit_mb * 1024.0

        judge0_submissions = []
        for tc in test_cases:
            stdin_b64 = base64.b64encode(tc["input"].encode()).decode()
            expected_b64 = base64.b64encode(
                tc["expected_output"].encode()
            ).decode()

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

        # ── 8. Submit batch to Judge0 ─────────────────────────────────────────
        logger.info(
            f"[submit] Sending {len(judge0_submissions)} test cases to Judge0: "
            f"cpu_limit={cpu_time_limit}s, wall_limit={wall_time_limit}s, "
            f"mem_limit={memory_limit}KB"
        )
        try:
            tokens = await self._judge0.create_batch_submissions(judge0_submissions)
        except Judge0Error as e:
            logger.error(f"[submit] Judge0 batch submit failed for submission {submission.id}: {e}")
            submission.verdict = SubmissionVerdict.INTERNAL_ERROR
            submission.error_message = str(e)
            await self._dao.update_submission(submission)
            raise JudgeServiceException(str(e))

        submission.judge0_tokens = ",".join(tokens)
        await self._dao.update_submission(submission)
        logger.info(f"[submit] Judge0 tokens saved: submission={submission.id}, tokens={len(tokens)}")

        # Phase 1 complete — polling and result processing happen in the ARQ task.
        return submission, test_cases, contest_problem.points, memory_limit

    async def run_code(
        self,
        contest_id: str,
        contest_problem_id: str,
        team_id: str,
        user_id: str,
        language: str,
        source_code: str,
    ) -> dict:
        """Run code against sample test cases only. No DB writes, no side effects.

        Same validation as submit_code() except the SOLVED check is skipped —
        users may run even after the problem is marked SOLVED.
        Returns a dict matching RunCodeResultData; nothing is persisted.
        """
        logger.info(
            f"[run] Starting: contest={contest_id}, problem={contest_problem_id}, "
            f"team={team_id}, user={user_id}, lang={language}, "
            f"code_len={len(source_code)} chars"
        )

        # ── 1. Validate contest is ACTIVE ─────────────────────────────────────
        contest = await self._dao.get_contest(contest_id)
        if not contest or contest.status != ContestStatus.ACTIVE:
            logger.warning(
                f"[run] Contest not active: {contest_id}, "
                f"status={contest.status if contest else 'NOT_FOUND'}"
            )
            raise ContestNotActiveException()

        # ── 2. Validate user has CODING role in team ──────────────────────────
        member = await self._dao.get_team_member(team_id, user_id)
        if not member or member.role != TeamRole.CODING:
            logger.warning(
                f"[run] User {user_id} not CODING role in team {team_id}, "
                f"role={member.role if member else 'NOT_MEMBER'}"
            )
            raise NotCodingRoleException()

        # ── 3. Validate assignment exists (SOLVED is OK for run) ──────────────
        assignment = await self._dao.get_assignment(contest_problem_id, team_id)
        if not assignment:
            logger.warning(f"[run] No assignment: problem={contest_problem_id}, team={team_id}")
            raise ProblemNotAssignedException()

        # ── 4. Validate language ──────────────────────────────────────────────
        language_lower = language.lower()
        if language_lower not in SUPPORTED_LANGUAGES:
            logger.warning(f"[run] Unsupported language: '{language}'")
            raise UnsupportedLanguageException(language)
        language_id = SUPPORTED_LANGUAGES[language_lower]

        # ── 5. Fetch test cases from GCS (via cache, same as submit) ──────────
        contest_problem = await self._dao.get_contest_problem(contest_problem_id)
        if not contest_problem:
            logger.warning(f"[run] Contest problem not found: {contest_problem_id}")
            raise NoTestCasesException()

        underlying_problem = contest_problem.resolved_problem
        if not underlying_problem or not underlying_problem.test_cases_url:
            logger.warning(
                f"[run] No test cases URL on underlying problem for {contest_problem_id}"
            )
            raise NoTestCasesException()

        gcs_url = underlying_problem.test_cases_url
        test_cases = await get_cached_test_cases(gcs_url)
        if test_cases is None:
            try:
                test_cases = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: storage_service.download_test_cases_from_url(gcs_url),
                )
            except StorageError as e:
                logger.error(f"[run] GCS download failed: {e}")
                raise NoTestCasesException()
            await set_cached_test_cases(gcs_url, test_cases)
            logger.info(f"[run] GCS cache miss — downloaded and cached {len(test_cases)} test cases")
        else:
            logger.info(f"[run] GCS cache hit — {len(test_cases)} test cases")

        if not test_cases:
            raise NoTestCasesException()

        # ── 6. Filter to sample test cases only ──────────────────────────────
        sample_cases = [tc for tc in test_cases if tc.get("is_sample", False)]
        if not sample_cases:
            logger.warning(f"[run] No sample test cases for problem {contest_problem_id}")
            raise NoSampleTestCasesException()
        logger.info(f"[run] Found {len(sample_cases)} sample test cases (of {len(test_cases)} total)")

        # ── 7. Build Judge0 batch request for sample cases only ───────────────
        source_b64 = base64.b64encode(source_code.encode()).decode()
        cpu_time_limit = contest_problem.time_limit_ms / 1000.0
        wall_time_limit = cpu_time_limit * 3
        memory_limit = contest_problem.memory_limit_mb * 1024.0

        judge0_submissions = []
        for tc in sample_cases:
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

        # ── 8. Submit to Judge0 and poll ──────────────────────────────────────
        logger.info(f"[run] Sending {len(judge0_submissions)} sample test cases to Judge0")
        try:
            tokens = await self._judge0.create_batch_submissions(judge0_submissions)
        except Judge0Error as e:
            logger.error(f"[run] Judge0 batch submit failed: {e}")
            raise JudgeServiceException(str(e))

        try:
            results = await self._judge0.poll_batch_fail_fast(tokens)
        except Judge0TimeoutError as e:
            logger.error(f"[run] Polling timed out: {e}")
            raise JudgeServiceException("Execution timed out")
        except Judge0Error as e:
            logger.error(f"[run] Polling failed: {e}")
            raise JudgeServiceException(str(e))

        # ── 9. Build in-memory result (NO DB writes) ──────────────────────────
        passed = 0
        max_time_ms = 0
        max_memory_kb = 0
        overall_verdict = "ACCEPTED"
        first_compile_output: str | None = None
        first_stderr: str | None = None
        first_error_message: str | None = None
        test_result_list = []

        for idx, (tc, result) in enumerate(zip(sample_cases, results)):
            # Still in-queue/processing when fail-fast exited — not evaluated.
            if result.status.id <= Judge0StatusId.PROCESSING:
                continue

            verdict_str = JUDGE0_TO_VERDICT.get(result.status.id, "INTERNAL_ERROR")
            stdout_decoded = _b64_decode(result.stdout)
            stderr_decoded = _b64_decode(result.stderr)
            compile_decoded = _b64_decode(result.compile_output)

            time_ms = int(result.time * 1000) if result.time else None
            memory_kb = int(result.memory) if result.memory else None

            if time_ms and time_ms > max_time_ms:
                max_time_ms = time_ms
            if memory_kb and memory_kb > max_memory_kb:
                max_memory_kb = memory_kb

            if verdict_str == "RUNTIME_ERROR" and memory_kb is not None and memory_kb >= memory_limit:
                verdict_str = "MEMORY_LIMIT_EXCEEDED"

            if result.status.id == Judge0StatusId.ACCEPTED:
                passed += 1
            elif overall_verdict == "ACCEPTED":
                overall_verdict = verdict_str
                first_compile_output = compile_decoded
                first_stderr = stderr_decoded
                first_error_message = result.message

            test_result_list.append({
                "test_case_index": idx,
                "verdict": verdict_str,
                "time_ms": time_ms,
                "memory_kb": memory_kb,
                "stdout": stdout_decoded,
                "stderr": stderr_decoded,
                "compile_output": compile_decoded,
                "input": tc["input"],
                "expected_output": tc["expected_output"],
            })

        logger.info(
            f"[run] Complete: passed={passed}/{len(sample_cases)}, "
            f"overall_verdict={overall_verdict}"
        )

        return {
            "language": language_lower,
            "passed": passed,
            "total": len(sample_cases),
            "overall_verdict": overall_verdict,
            "max_time_ms": max_time_ms if max_time_ms else None,
            "max_memory_kb": max_memory_kb if max_memory_kb else None,
            "compile_output": first_compile_output,
            "stderr": first_stderr,
            "error_message": first_error_message,
            "test_results": test_result_list,
        }

    async def process_judging_result(
        self,
        submission_id: str,
        test_cases: list[dict],
        points: int,
        memory_limit_kb: float,
    ) -> Submission:
        """Phase 2: poll Judge0, process results, update DB, broadcast leaderboard.

        Called by the ARQ background task after submit_code() completes Phase 1.
        """
        submission = await self._dao.get_submission_by_id(submission_id)
        if not submission:
            raise SubmissionNotFoundException(submission_id)

        tokens = submission.judge0_tokens.split(",") if submission.judge0_tokens else []
        if not tokens:
            logger.error(f"[judge] No tokens found for submission {submission_id}")
            submission.verdict = SubmissionVerdict.INTERNAL_ERROR
            submission.error_message = "No Judge0 tokens available"
            submission.judged_at = datetime.now()
            await self._dao.update_submission(submission)
            return submission

        # ── 9. Poll until done or first failure ───────────────────────────────
        try:
            results = await self._judge0.poll_batch_fail_fast(tokens)
        except Judge0TimeoutError as e:
            logger.error(f"[judge] Polling timed out for submission {submission_id}: {e}")
            submission.verdict = SubmissionVerdict.INTERNAL_ERROR
            submission.error_message = "Execution timed out waiting for results"
            submission.judged_at = datetime.now()
            await self._dao.update_submission(submission)
            raise JudgeServiceException("Execution timed out")
        except Judge0Error as e:
            logger.error(f"[judge] Polling failed for submission {submission_id}: {e}")
            submission.verdict = SubmissionVerdict.INTERNAL_ERROR
            submission.error_message = str(e)
            submission.judged_at = datetime.now()
            await self._dao.update_submission(submission)
            raise JudgeServiceException(str(e))

        # ── 10. Process results ───────────────────────────────────────────────
        logger.info(f"[judge] Processing {len(results)} Judge0 results for submission {submission_id}")
        passed = 0
        max_time_ms = 0
        max_memory_kb = 0
        overall_verdict = SubmissionVerdict.ACCEPTED
        first_error_output = None
        test_result_records = []

        for idx, (tc, result) in enumerate(zip(test_cases, results)):
            # Still in-queue/processing when fail-fast exited — not evaluated.
            if result.status.id <= Judge0StatusId.PROCESSING:
                continue

            verdict_str = JUDGE0_TO_VERDICT.get(result.status.id, "INTERNAL_ERROR")

            stdout_decoded = _b64_decode(result.stdout)
            stderr_decoded = _b64_decode(result.stderr)
            compile_decoded = _b64_decode(result.compile_output)

            time_ms = int(result.time * 1000) if result.time else None
            memory_kb = int(result.memory) if result.memory else None

            if time_ms and time_ms > max_time_ms:
                max_time_ms = time_ms
            if memory_kb and memory_kb > max_memory_kb:
                max_memory_kb = memory_kb

            # Judge0 CE has no native MLE status — memory overflows are reported as
            # runtime errors (SIGSEGV, SIGABRT, etc.). Reclassify when memory usage
            # meets or exceeds the limit we sent.
            if verdict_str == "RUNTIME_ERROR" and memory_kb is not None and memory_kb >= memory_limit_kb:
                verdict_str = "MEMORY_LIMIT_EXCEEDED"

            if result.status.id == Judge0StatusId.ACCEPTED:
                passed += 1
            elif overall_verdict == SubmissionVerdict.ACCEPTED:
                overall_verdict = SubmissionVerdict(verdict_str)
                first_error_output = {
                    "stderr": stderr_decoded,
                    "compile_output": compile_decoded,
                    "message": result.message,
                }

            logger.debug(
                f"[judge] TC#{idx}: verdict={verdict_str}, "
                f"time={time_ms}ms, memory={memory_kb}KB, "
                f"status_id={result.status.id}"
            )

            is_sample = bool(tc.get("is_sample", False))
            test_result_records.append(
                SubmissionTestResult(
                    submission_id=submission.id,
                    test_case_index=idx,
                    judge0_token=result.token,
                    status_id=result.status.id,
                    verdict=verdict_str,
                    stdout=stdout_decoded,
                    stderr=stderr_decoded,
                    compile_output=compile_decoded,
                    time_ms=time_ms,
                    memory_kb=memory_kb,
                    is_sample=is_sample,
                    input=tc["input"] if is_sample else None,
                    expected_output=tc["expected_output"] if is_sample else None,
                )
            )

        # ── 11. Save test results ─────────────────────────────────────────────
        await self._dao.create_test_results(test_result_records)
        logger.debug(f"[judge] Saved {len(test_result_records)} test result records to DB")

        submission.test_results = test_result_records

        # ── 12. Update submission with final verdict ──────────────────────────
        submission.verdict = overall_verdict
        submission.passed_test_cases = passed
        submission.max_time_ms = max_time_ms if max_time_ms else None
        submission.max_memory_kb = max_memory_kb if max_memory_kb else None
        submission.judged_at = datetime.now()

        if first_error_output:
            submission.stderr = first_error_output.get("stderr")
            submission.compile_output = first_error_output.get("compile_output")
            submission.error_message = first_error_output.get("message")

        await self._dao.update_submission(submission)

        # ── 13. If ACCEPTED → update assignment + score ───────────────────────
        if overall_verdict == SubmissionVerdict.ACCEPTED:
            await self._dao.mark_assignment_solved_and_add_score(
                assignment_id=submission.assignment_id,
                team_id=submission.team_id,
                contest_id=submission.contest_id,
                points=points,
            )
            logger.info(
                f"[judge] ACCEPTED: submission={submission_id}, "
                f"+{points}pts for team {submission.team_id}, "
                f"passed={passed}/{len(test_cases)}, "
                f"max_time={max_time_ms}ms, max_memory={max_memory_kb}KB"
            )
            await broadcast_leaderboard(submission.contest_id)
        else:
            logger.info(
                f"[judge] REJECTED: submission={submission_id}, "
                f"verdict={overall_verdict.value}, "
                f"passed={passed}/{len(test_cases)}, "
                f"max_time={max_time_ms}ms, max_memory={max_memory_kb}KB"
            )

        return submission

    async def get_submission(self, submission_id: str) -> Submission:
        submission = await self._dao.get_submission_by_id(submission_id)
        if not submission:
            raise SubmissionNotFoundException(submission_id)
        return submission

    async def list_submissions_for_problem(
        self, contest_problem_id: str, team_id: str
    ) -> list[Submission]:
        assignment = await self._dao.get_assignment(contest_problem_id, team_id)
        if not assignment:
            return []
        return await self._dao.list_submissions_for_assignment(assignment.id)

    async def list_submissions_for_team(
        self, team_id: str, contest_id: str
    ) -> list[Submission]:
        return await self._dao.list_submissions_for_team_in_contest(
            team_id, contest_id
        )

    async def get_latest_solution(
        self,
        team_id: str,
        contest_problem_id: str,
        requester_user_id: str,
        is_organizer: bool,
    ) -> TeamProblemSolution:
        """Return the latest submitted code for (team, problem).

        Authorized for team members and organizers.
        """
        if not is_organizer:
            member = await self._dao.get_team_member(team_id, requester_user_id)
            if not member:
                raise NotAllowedToViewCodeException()

        solution = await self._dao.get_solution_by_team_and_problem(
            team_id, contest_problem_id
        )
        if not solution:
            raise LatestSolutionNotFoundException()
        return solution


# ── Helpers ───────────────────────────────────────────────────────────────────


def _b64_decode(value: str | None) -> str | None:
    """Safely decode a base64-encoded string from Judge0."""
    if not value:
        return None
    try:
        return base64.b64decode(value).decode("utf-8", errors="replace")
    except Exception:
        return value  # Return raw if decoding fails


# ── Dependency ────────────────────────────────────────────────────────────────

# Global Judge0 client instance (initialized in app lifespan)
judge0_client = Judge0Client()


async def get_submission_service(
    dao: SubmissionDAO = Depends(get_submission_dao),
) -> SubmissionService:
    return SubmissionService(dao=dao, judge0=judge0_client)
