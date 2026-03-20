"""Problems Handler Layer"""

import logging
from typing import Optional

from fastapi import Body, Depends, Path, Query

from app.api.auth.dependencies import get_current_user
from app.api.auth.schemas import UserWithPermissions
from app.api.problems.schemas.problems import (
    BuiltinProblemListResponse,
    BuiltinProblemResponseData,
    ProblemCreateRequest,
    ProblemListResponse,
    ProblemResponse,
    ProblemResponseData,
    ProblemUpdateRequest,
)
from app.api.problems.services.problems import (
    BuiltinProblemService,
    ProblemService,
    get_builtin_problem_service,
    get_problem_service,
)
from app.core.enums import Difficulty

logger = logging.getLogger(__name__)


async def create_problem_handler(
    request: ProblemCreateRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    problem_service: ProblemService = Depends(get_problem_service),
) -> ProblemResponse:
    """Create a new reusable coding problem. Slug is auto-generated."""
    problem = await problem_service.create_problem(
        title=request.data.title,
        description=request.data.description,
        difficulty=request.data.difficulty,
        points=request.data.points,
        base_price=request.data.base_price,
        created_by=current_user.user_id,
        time_limit_ms=request.data.time_limit_ms or 2000,
        memory_limit_mb=request.data.memory_limit_mb or 256,
    )
    logger.info(f"Problem '{problem.title}' created by user {current_user.user_id}")
    return ProblemResponse(data=ProblemResponseData.model_validate(problem))


async def list_problems_handler(
    difficulty: Optional[Difficulty] = Query(default=None),
    search: Optional[str] = Query(default=None),
    created_by: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: UserWithPermissions = Depends(get_current_user),
    problem_service: ProblemService = Depends(get_problem_service),
) -> ProblemListResponse:
    """List problems with optional filters: difficulty, search, created_by, pagination."""
    problems = await problem_service.list_problems(
        difficulty=difficulty,
        search=search,
        created_by=created_by,
        page=page,
        limit=limit,
    )
    return ProblemListResponse(
        data=[ProblemResponseData.model_validate(p) for p in problems]
    )


async def get_problem_handler(
    problem_id: str = Path(..., description="Problem ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    problem_service: ProblemService = Depends(get_problem_service),
) -> ProblemResponse:
    """Get a problem by ID."""
    problem = await problem_service.get_problem_by_id(problem_id)
    return ProblemResponse(data=ProblemResponseData.model_validate(problem))


async def update_problem_handler(
    problem_id: str = Path(..., description="Problem ID"),
    request: ProblemUpdateRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    problem_service: ProblemService = Depends(get_problem_service),
) -> ProblemResponse:
    """Update a problem. Only the creator may update."""
    update_data = request.data.model_dump(exclude_none=True)
    problem = await problem_service.update_problem(
        problem_id=problem_id,
        requesting_user_id=current_user.user_id,
        **update_data,
    )
    logger.info(f"Problem {problem_id} updated by {current_user.user_id}")
    return ProblemResponse(data=ProblemResponseData.model_validate(problem))


async def delete_problem_handler(
    problem_id: str = Path(..., description="Problem ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    problem_service: ProblemService = Depends(get_problem_service),
) -> ProblemResponse:
    """Soft-delete a problem (is_active=False). Only the creator may delete."""
    problem = await problem_service.soft_delete_problem(
        problem_id=problem_id,
        requesting_user_id=current_user.user_id,
    )
    logger.info(f"Problem {problem_id} soft-deleted by {current_user.user_id}")
    return ProblemResponse(data=ProblemResponseData.model_validate(problem))


async def list_builtin_problems_handler(
    difficulty: Optional[Difficulty] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: UserWithPermissions = Depends(get_current_user),
    builtin_service: BuiltinProblemService = Depends(get_builtin_problem_service),
) -> BuiltinProblemListResponse:
    """List all active built-in problems. Supports difficulty and search filters."""
    problems = await builtin_service.list_builtin_problems(
        difficulty=difficulty,
        search=search,
        page=page,
        limit=limit,
    )
    return BuiltinProblemListResponse(
        data=[BuiltinProblemResponseData.model_validate(p) for p in problems]
    )
