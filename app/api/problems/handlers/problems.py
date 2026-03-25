"""Built-in Problems Handler Layer"""

import logging
from typing import Optional

from fastapi import Depends, Path, Query

from app.api.auth.dependencies import get_current_user
from app.api.auth.schemas import UserWithPermissions
from app.api.problems.schemas.problems import (
    BuiltinProblemListResponse,
    BuiltinProblemResponse,
    BuiltinProblemResponseData,
)
from app.api.problems.services.problems import (
    BuiltinProblemService,
    get_builtin_problem_service,
)
from app.core.enums import Difficulty
from app.core.responses import MetaResponse

logger = logging.getLogger(__name__)


async def list_builtin_problems_handler(
    difficulty: Optional[Difficulty] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: UserWithPermissions = Depends(get_current_user),
    builtin_service: BuiltinProblemService = Depends(get_builtin_problem_service),
) -> BuiltinProblemListResponse:
    """List all active built-in problems. Supports difficulty and search filters."""
    problems, total = await builtin_service.list_builtin_problems(
        difficulty=difficulty,
        search=search,
        page=page,
        limit=limit,
    )
    return BuiltinProblemListResponse(
        data=[BuiltinProblemResponseData.model_validate(p) for p in problems],
        meta=MetaResponse(page=page, limit=limit, total=total),
    )


async def get_builtin_problem_handler(
    problem_id: str = Path(..., description="Problem ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    builtin_service: BuiltinProblemService = Depends(get_builtin_problem_service),
) -> BuiltinProblemResponse:
    """Get a single built-in problem by ID."""
    problem = await builtin_service.get_builtin_problem_by_id(problem_id)
    return BuiltinProblemResponse(
        data=BuiltinProblemResponseData.model_validate(problem)
    )
