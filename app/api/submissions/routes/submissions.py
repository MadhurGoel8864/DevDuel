"""Submissions API Routes"""

from fastapi import APIRouter

from app.api.submissions.handlers.submissions import (
    get_latest_solution_handler,
    get_submission_handler,
    list_submissions_for_problem_handler,
    list_submissions_for_team_handler,
    submit_code_handler,
)

router = APIRouter(prefix="/submissions", tags=["Submissions"])

# Submit code for judging
router.add_api_route(
    "/contests/{contest_id}/problems/{contest_problem_id}/submit",
    submit_code_handler,
    methods=["POST"],
    status_code=201,
)

# Get the latest submitted code for a team on a problem (must precede /{submission_id})
router.add_api_route(
    "/contests/{contest_id}/problems/{contest_problem_id}/teams/{team_id}/latest-code",
    get_latest_solution_handler,
    methods=["GET"],
)

# List submissions by team for a specific problem
router.add_api_route(
    "/contests/{contest_id}/problems/{contest_problem_id}/teams/{team_id}",
    list_submissions_for_problem_handler,
    methods=["GET"],
)

# List all submissions by team in a contest
router.add_api_route(
    "/contests/{contest_id}/teams/{team_id}",
    list_submissions_for_team_handler,
    methods=["GET"],
)

# Get submission details (with test results) — generic /{submission_id}, register last
router.add_api_route(
    "/{submission_id}",
    get_submission_handler,
    methods=["GET"],
)
