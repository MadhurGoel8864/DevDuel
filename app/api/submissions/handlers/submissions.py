"""Submissions Handler Layer"""

import logging

from fastapi import Body, Depends, Path

from app.api.auth.dependencies import get_current_user
from app.api.auth.schemas import UserWithPermissions
from app.api.bidding.services.event_bus import fanout_bidding_event
from app.api.submissions.schemas.submissions import (
    LatestSolutionResponse,
    LatestSolutionResponseData,
    RunCodeRequest,
    RunCodeResponse,
    RunCodeResultData,
    RunTestCaseResultData,
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
    """Submit code for judging. Blocks until Judge0 finishes and returns the full result."""
    submission, test_cases, points = await service.submit_code(
        contest_id=contest_id,
        contest_problem_id=contest_problem_id,
        team_id=request.data.team_id,
        user_id=current_user.user_id,
        language=request.data.language,
        source_code=request.data.source_code,
    )

    submission = await service.process_judging_result(
        submission_id=submission.id,
        test_cases=test_cases,
        points=points,
    )

    await fanout_bidding_event(
        contest_id=contest_id,
        payload={
            "type": "SUBMISSION_RESULT",
            "submission_id": submission.id,
            "verdict": submission.verdict.value,
            "passed_test_cases": submission.passed_test_cases,
            "total_test_cases": submission.total_test_cases,
        },
    )

    data = SubmissionDetailResponseData.model_validate(submission)
    data.test_results = [
        TestResultResponseData.model_validate(tr)
        for tr in submission.test_results
    ]
    return SubmissionDetailResponse(data=data)


async def run_code_handler(
    contest_id: str = Path(..., description="Contest ID"),
    contest_problem_id: str = Path(..., description="Contest Problem ID"),
    request: RunCodeRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    service: SubmissionService = Depends(get_submission_service),
) -> RunCodeResponse:
    """Run code against sample test cases only. No submission record is created.

    Allowed even if the problem is already SOLVED. Returns results synchronously.
    """
    result = await service.run_code(
        contest_id=contest_id,
        contest_problem_id=contest_problem_id,
        team_id=request.data.team_id,
        user_id=current_user.user_id,
        language=request.data.language,
        source_code=request.data.source_code,
    )
    data = RunCodeResultData.model_validate(result)
    data.test_results = [
        RunTestCaseResultData.model_validate(tr)
        for tr in result["test_results"]
    ]
    return RunCodeResponse(data=data)


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
