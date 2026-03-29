"""Submissions Handler Layer"""

import logging

from fastapi import Body, Depends, Path

from app.api.auth.dependencies import get_current_user
from app.api.auth.schemas import UserWithPermissions
from app.api.submissions.schemas.submissions import (
    SubmissionDetailResponse,
    SubmissionDetailResponseData,
    SubmissionListItem,
    SubmissionListResponse,
    SubmitCodeRequest,
    TestResultResponseData,
)
from app.api.submissions.services.submissions import (
    SubmissionService,
    get_submission_service,
)

logger = logging.getLogger(__name__)


async def submit_code_handler(
    contest_id: str = Path(..., description="Contest ID"),
    contest_problem_id: str = Path(..., description="Contest Problem ID"),
    request: SubmitCodeRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    service: SubmissionService = Depends(get_submission_service),
) -> SubmissionDetailResponse:
    """Submit code for judging against a contest problem.

    Returns the fully-judged submission including per-test-case results
    in a single response — no second API call required.
    """
    submission = await service.submit_code(
        contest_id=contest_id,
        contest_problem_id=contest_problem_id,
        team_id=request.data.team_id,
        user_id=current_user.user_id,
        language=request.data.language,
        source_code=request.data.source_code,
    )
    data = SubmissionDetailResponseData.model_validate(submission)
    data.test_results = [
        TestResultResponseData.model_validate(tr)
        for tr in (submission.test_results or [])
    ]
    return SubmissionDetailResponse(data=data)


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
