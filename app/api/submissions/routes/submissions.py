"""Submissions API Routes"""

from fastapi import APIRouter, Depends

from app.api.submissions.handlers.submissions import (
    get_latest_solution_handler,
    get_submission_handler,
    list_submissions_for_problem_handler,
    list_submissions_for_team_handler,
    run_code_handler,
    submit_code_handler,
)
from app.core.config import settings
from app.core.rate_limit import rate_limit

router = APIRouter(prefix="/submissions", tags=["Submissions"])

# Submit code for judging — dual limit keyed per user:
#   burst  : prevents rapid resubmission (accidental double-click, scripted spam)
#   sustained: caps hourly Judge0 consumption per user
router.add_api_route(
    "/contests/{contest_id}/problems/{contest_problem_id}/submit",
    submit_code_handler,
    methods=["POST"],
    status_code=200,
    dependencies=[
        Depends(rate_limit("submit:burst", settings.SUBMIT_BURST_RATE_LIMIT, 8, by="user")),
        Depends(rate_limit("submit:sustained", settings.SUBMIT_SUSTAINED_RATE_LIMIT, 3600, by="user")),
    ],
)

# Run code against sample test cases only — no DB writes, no side effects
router.add_api_route(
    "/contests/{contest_id}/problems/{contest_problem_id}/run",
    run_code_handler,
    methods=["POST"],
    status_code=200,
    dependencies=[
        Depends(rate_limit("run:burst", settings.RUN_BURST_RATE_LIMIT, 5, by="user")),
        Depends(rate_limit("run:sustained", settings.RUN_SUSTAINED_RATE_LIMIT, 3600, by="user")),
    ],
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
