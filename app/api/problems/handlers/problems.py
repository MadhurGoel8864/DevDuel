"""Built-in Problems Handler Layer"""

import logging
from typing import Optional

from fastapi import Body, Depends, Path, Query

from app.api.auth.dependencies import get_current_user, require_organizer
from app.api.auth.schemas import UserWithPermissions
from app.api.problems.schemas.problems import (
    BuiltinProblemCreateRequest,
    BuiltinProblemListResponse,
    BuiltinProblemResponse,
    BuiltinProblemResponseData,
    BuiltinProblemUpdateRequest,
)
from app.api.problems.services.problems import (
    BuiltinProblemService,
    get_builtin_problem_service,
)
from app.core.enums import Difficulty
from app.core.responses import APIResponse, MetaResponse

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


async def create_builtin_problem_handler(
    request: BuiltinProblemCreateRequest = Body(...),
    current_user: UserWithPermissions = Depends(require_organizer),
    builtin_service: BuiltinProblemService = Depends(get_builtin_problem_service),
) -> BuiltinProblemResponse:
    """Create a new built-in (platform-curated) problem. Requires organizer role."""
    problem = await builtin_service.create(data=request.data)
    return BuiltinProblemResponse(
        data=BuiltinProblemResponseData.model_validate(problem)
    )


async def update_builtin_problem_handler(
    problem_id: str = Path(..., description="Built-in Problem ID"),
    request: BuiltinProblemUpdateRequest = Body(...),
    current_user: UserWithPermissions = Depends(require_organizer),
    builtin_service: BuiltinProblemService = Depends(get_builtin_problem_service),
) -> BuiltinProblemResponse:
    """Update a built-in problem. Slug regenerates only on title change."""
    updated = await builtin_service.update(problem_id=problem_id, data=request.data)
    return BuiltinProblemResponse(
        data=BuiltinProblemResponseData.model_validate(updated)
    )


async def delete_builtin_problem_handler(
    problem_id: str = Path(..., description="Built-in Problem ID"),
    current_user: UserWithPermissions = Depends(require_organizer),
    builtin_service: BuiltinProblemService = Depends(get_builtin_problem_service),
) -> APIResponse[dict]:
    """Hard-delete a built-in problem. Contest references cascade automatically."""
    await builtin_service.delete(problem_id=problem_id)
    return APIResponse[dict](data={"id": problem_id})
