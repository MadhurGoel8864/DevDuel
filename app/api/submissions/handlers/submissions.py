"""Submissions Handler Layer"""

import logging

from arq.connections import ArqRedis
from fastapi import Body, Depends, Path

from app.api.auth.dependencies import get_current_user
from app.api.auth.schemas import UserWithPermissions
from app.api.submissions.schemas.submissions import (
    LatestSolutionResponse,
    LatestSolutionResponseData,
    SubmissionDetailResponse,
    SubmissionDetailResponseData,
    SubmissionListItem,
    SubmissionListResponse,
    SubmitCodeAcceptedData,
    SubmitCodeAcceptedResponse,
    SubmitCodeRequest,
    TestResultResponseData,
)
from app.api.submissions.services.submissions import (
    SubmissionService,
    get_submission_service,
)
from app.core.arq_pool import get_arq_pool_dep
from app.core.enums import SubmissionVerdict

logger = logging.getLogger(__name__)


async def submit_code_handler(
    contest_id: str = Path(..., description="Contest ID"),
    contest_problem_id: str = Path(..., description="Contest Problem ID"),
    request: SubmitCodeRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    service: SubmissionService = Depends(get_submission_service),
    arq_pool: ArqRedis = Depends(get_arq_pool_dep),
) -> SubmitCodeAcceptedResponse:
    """Accept a code submission for background judging.

    Returns 202 immediately with verdict=PENDING.
    Results are delivered via the bidding WebSocket as a SUBMISSION_RESULT event.
    """
    submission, test_cases, points = await service.submit_code(
        contest_id=contest_id,
        contest_problem_id=contest_problem_id,
        team_id=request.data.team_id,
        user_id=current_user.user_id,
        language=request.data.language,
        source_code=request.data.source_code,
    )

    await arq_pool.enqueue_job(
        "process_submission_task",
        submission_id=submission.id,
        test_cases=test_cases,
        points=points,
        contest_id=contest_id,
        _job_id=submission.id,  # idempotency — prevents duplicate processing
    )

    return SubmitCodeAcceptedResponse(
        data=SubmitCodeAcceptedData(
            submission_id=submission.id,
            verdict=SubmissionVerdict.PENDING,
            message="Submission accepted. Results will be delivered via WebSocket.",
        )
    )


async def get_submission_handler(
    submission_id: str = Path(..., description="Submission ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    service: SubmissionService = Depends(get_submission_service),
) -> SubmissionDetailResponse:
    """Get full submission details including per-test-case results."""
    submission = await service.get_submission(submission_id)

    data = SubmissionDetailResponseData.model_validate(submission)
    data.test_results = [
        TestResultResponseData.model_validate(tr)
        for tr in submission.test_results
    ]
    return SubmissionDetailResponse(data=data)


async def list_submissions_for_problem_handler(
    contest_id: str = Path(..., description="Contest ID"),
    contest_problem_id: str = Path(..., description="Contest Problem ID"),
    team_id: str = Path(..., description="Team ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    service: SubmissionService = Depends(get_submission_service),
) -> SubmissionListResponse:
    """List all submissions by a team for a specific problem."""
    submissions = await service.list_submissions_for_problem(
        contest_problem_id=contest_problem_id,
        team_id=team_id,
    )
    return SubmissionListResponse(
        data=[SubmissionListItem.model_validate(s) for s in submissions]
    )


async def list_submissions_for_team_handler(
    contest_id: str = Path(..., description="Contest ID"),
    team_id: str = Path(..., description="Team ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    service: SubmissionService = Depends(get_submission_service),
) -> SubmissionListResponse:
    """List all submissions by a team across all problems in a contest."""
    submissions = await service.list_submissions_for_team(
        team_id=team_id,
        contest_id=contest_id,
    )
    return SubmissionListResponse(
        data=[SubmissionListItem.model_validate(s) for s in submissions]
    )


async def get_latest_solution_handler(
    contest_id: str = Path(..., description="Contest ID"),
    contest_problem_id: str = Path(..., description="Contest Problem ID"),
    team_id: str = Path(..., description="Team ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    service: SubmissionService = Depends(get_submission_service),
) -> LatestSolutionResponse:
    """Return the team's latest submitted code for a contest problem.

    Used by the coding editor (rehydrate on reload) and by organizers
    (review what a team submitted). Authorized for team members and organizers.
    """
    solution = await service.get_latest_solution(
        team_id=team_id,
        contest_problem_id=contest_problem_id,
        requester_user_id=current_user.user_id,
        is_organizer=current_user.is_organizer,
    )
    return LatestSolutionResponse(
        data=LatestSolutionResponseData.model_validate(solution)
    )
