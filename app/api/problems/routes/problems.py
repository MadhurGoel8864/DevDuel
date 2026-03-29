"""Problems API Routes"""

from fastapi import APIRouter

from app.api.problems.handlers.contest_problems import (
    import_builtin_problem_handler,
    list_contest_problems_handler,
    remove_problem_from_contest_handler,
    update_contest_problem_handler,
)
from app.api.problems.handlers.problems import (
    get_builtin_problem_handler,
    list_builtin_problems_handler,
)
from app.api.problems.handlers.test_cases import upload_test_cases_handler

# ── /api/problems ─────────────────────────────────────────────────────────────
problems_router = APIRouter(prefix="/problems", tags=["Problems"])

problems_router.add_api_route(
    "/builtin/problems", list_builtin_problems_handler, methods=["GET"]
)
problems_router.add_api_route(
    "/{problem_id}", get_builtin_problem_handler, methods=["GET"]
)
problems_router.add_api_route(
    "/{problem_id}/test-cases",
    upload_test_cases_handler,
    methods=["POST"],
    status_code=201,
    tags=["Test Cases"],
)

# ── /api/contests/{contest_id}/problems ────────────────────────────────────────
contest_problems_router = APIRouter(
    prefix="/contests/{contest_id}/problems", tags=["Contest Problems"]
)

contest_problems_router.add_api_route(
    "/import",
    import_builtin_problem_handler,
    methods=["POST"],
    status_code=201,
)
contest_problems_router.add_api_route(
    "", list_contest_problems_handler, methods=["GET"]
)
contest_problems_router.add_api_route(
    "/{contest_problem_id}",
    remove_problem_from_contest_handler,
    methods=["DELETE"],
)
contest_problems_router.add_api_route(
    "/{contest_problem_id}",
    update_contest_problem_handler,
    methods=["PUT"],
)
