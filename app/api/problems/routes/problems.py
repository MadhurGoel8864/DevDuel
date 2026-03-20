"""Problems API Routes"""

from fastapi import APIRouter

from app.api.problems.handlers.contest_problems import (
    add_problem_to_contest_handler,
    import_builtin_problem_handler,
    list_contest_problems_handler,
    remove_problem_from_contest_handler,
)
from app.api.problems.handlers.problems import (
    create_problem_handler,
    delete_problem_handler,
    get_problem_handler,
    list_builtin_problems_handler,
    list_problems_handler,
    update_problem_handler,
)

# ── /api/problems ──────────────────────────────────────────────────────────────
problems_router = APIRouter(prefix="/problems", tags=["Problems"])

problems_router.add_api_route(
    "", create_problem_handler, methods=["POST"], status_code=201
)
problems_router.add_api_route("", list_problems_handler, methods=["GET"])
problems_router.add_api_route("/{problem_id}", get_problem_handler, methods=["GET"])
problems_router.add_api_route("/{problem_id}", update_problem_handler, methods=["PUT"])
problems_router.add_api_route(
    "/{problem_id}", delete_problem_handler, methods=["DELETE"]
)

# ── /api/problems/builtin ──────────────────────────────────────────────────────
builtin_problems_router = APIRouter(prefix="/builtin", tags=["Built-in Problems"])

builtin_problems_router.add_api_route(
    "/problems", list_builtin_problems_handler, methods=["GET"]
)

# ── /api/contests/{contest_id}/problems ────────────────────────────────────────
contest_problems_router = APIRouter(
    prefix="/contests/{contest_id}/problems", tags=["Contest Problems"]
)

contest_problems_router.add_api_route(
    "", add_problem_to_contest_handler, methods=["POST"], status_code=201
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
    "/import",
    import_builtin_problem_handler,
    methods=["POST"],
    status_code=201,
)
