# app/workers/tasks/submission.py
"""ARQ task: poll Judge0 and finalize a submission.

Triggered by submit_code_handler after Phase 1 (batch submission to Judge0) completes.
Runs in a separate worker process so the HTTP request returns immediately.
"""
import logging

from app.api.bidding.services.event_bus import fanout_bidding_event
from app.api.submissions.dao.submissions import SubmissionDAO
from app.api.submissions.services.submissions import JudgeServiceException, SubmissionService
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def process_submission_task(
    ctx: dict,
    submission_id: str,
    test_cases: list[dict],
    points: int,
    contest_id: str,
) -> dict:
    """Poll Judge0, process results, update DB, broadcast leaderboard.

    ctx["judge0"] is the Judge0Client singleton injected by WorkerSettings.on_startup.
    """
    judge0 = ctx["judge0"]
    logger.info(f"[task:submission] starting: submission={submission_id}")

    try:
        async with AsyncSessionLocal() as session:
            dao = SubmissionDAO(session)
            service = SubmissionService(dao=dao, judge0=judge0)
            submission = await service.process_judging_result(
                submission_id=submission_id,
                test_cases=test_cases,
                points=points,
            )

        logger.info(
            f"[task:submission] done: submission={submission_id}, "
            f"verdict={submission.verdict.value}"
        )

        await fanout_bidding_event(
            contest_id=contest_id,
            payload={
                "type": "SUBMISSION_RESULT",
                "submission_id": submission_id,
                "verdict": submission.verdict.value,
                "passed_test_cases": submission.passed_test_cases,
                "total_test_cases": submission.total_test_cases,
            },
        )

        return {"submission_id": submission_id, "verdict": submission.verdict.value}

    except JudgeServiceException:
        # JudgeServiceException already logged and DB updated with INTERNAL_ERROR
        # Re-raise so ARQ can retry (up to max_tries)
        await fanout_bidding_event(
            contest_id=contest_id,
            payload={
                "type": "SUBMISSION_RESULT",
                "submission_id": submission_id,
                "verdict": "INTERNAL_ERROR",
                "passed_test_cases": 0,
                "total_test_cases": 0,
            },
        )
        raise

    except Exception as exc:
        logger.error(
            f"[task:submission] unexpected error: submission={submission_id}: {exc!r}",
            exc_info=True,
        )
        raise
