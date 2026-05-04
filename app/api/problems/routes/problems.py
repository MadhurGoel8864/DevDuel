"""Problems API Routes"""

from fastapi import APIRouter

from app.api.problems.handlers.contest_problems import (
    import_problem_handler,
    list_contest_problems_handler,
    remove_problem_from_contest_handler,
    update_contest_problem_handler,
)
from app.api.problems.handlers.custom_problems import (
    create_custom_problem_handler,
    delete_custom_problem_handler,
    get_custom_problem_handler,
    list_my_custom_problems_handler,
    update_custom_problem_handler,
)
from app.api.problems.handlers.problems import (
    get_builtin_problem_handler,
    list_builtin_problems_handler,
)
from app.api.problems.handlers.test_cases import (
    get_custom_test_cases_handler,
    get_test_cases_handler,
    upload_custom_test_cases_handler,
    upload_test_cases_handler,
)

# ── /api/problems ─────────────────────────────────────────────────────────────
problems_router = APIRouter(prefix="/problems", tags=["Problems"])

# Built-in catalog
problems_router.add_api_route(
    "/builtin/problems", list_builtin_problems_handler, methods=["GET"]
)

# Custom (admin-authored) problems CRUD — must be declared BEFORE the
# `/{problem_id}` catch-all below or FastAPI will route /problems/custom to it.
problems_router.add_api_route(
    "/custom",
    create_custom_problem_handler,
    methods=["POST"],
    status_code=201,
    tags=["Custom Problems"],
)
problems_router.add_api_route(
    "/custom",
    list_my_custom_problems_handler,
    methods=["GET"],
    tags=["Custom Problems"],
)
problems_router.add_api_route(
    "/custom/{custom_problem_id}",
    get_custom_problem_handler,
    methods=["GET"],
    tags=["Custom Problems"],
)
problems_router.add_api_route(
    "/custom/{custom_problem_id}",
    update_custom_problem_handler,
    methods=["PUT"],
    tags=["Custom Problems"],
)
problems_router.add_api_route(
    "/custom/{custom_problem_id}",
    delete_custom_problem_handler,
    methods=["DELETE"],
    tags=["Custom Problems"],
)
problems_router.add_api_route(
    "/custom/{custom_problem_id}/test-cases",
    upload_custom_test_cases_handler,
    methods=["POST"],
    status_code=201,
    tags=["Custom Problems", "Test Cases"],
)
problems_router.add_api_route(
    "/custom/{custom_problem_id}/test-cases",
    get_custom_test_cases_handler,
    methods=["GET"],
    tags=["Custom Problems", "Test Cases"],
)

# Built-in problem detail + test cases (catch-all `/{problem_id}` last)
problems_router.add_api_route(
    "/{problem_id}", get_builtin_problem_handler, methods=["GET"]
)
problems_router.add_api_route(
    "/{problem_id}/test-cases",
    get_test_cases_handler,
    methods=["GET"],
    tags=["Test Cases"],
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
    import_problem_handler,
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
