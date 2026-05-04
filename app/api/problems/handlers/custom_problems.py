"""Custom (admin-authored) Problems Handler Layer"""

import logging

from fastapi import Body, Depends, Path

from app.api.auth.dependencies import require_organizer
from app.api.auth.schemas import UserWithPermissions
from app.api.problems.schemas.problems import (
    CustomProblemCreateRequest,
    CustomProblemListResponse,
    CustomProblemResponse,
    CustomProblemResponseData,
    CustomProblemUpdateRequest,
)
from app.api.problems.services.problems import (
    CustomProblemService,
    get_custom_problem_service,
)
from app.core.responses import APIResponse

logger = logging.getLogger(__name__)


async def create_custom_problem_handler(
    request: CustomProblemCreateRequest = Body(...),
    current_user: UserWithPermissions = Depends(require_organizer),
    service: CustomProblemService = Depends(get_custom_problem_service),
) -> CustomProblemResponse:
    """Create a new admin-authored problem owned by the requesting organizer."""
    problem = await service.create(user_id=current_user.user_id, data=request.data)
    return CustomProblemResponse(
        data=CustomProblemResponseData.model_validate(problem)
    )


async def list_my_custom_problems_handler(
    current_user: UserWithPermissions = Depends(require_organizer),
    service: CustomProblemService = Depends(get_custom_problem_service),
) -> CustomProblemListResponse:
    """List all custom problems owned by the requesting organizer."""
    problems = await service.list_mine(current_user.user_id)
    return CustomProblemListResponse(
        data=[CustomProblemResponseData.model_validate(p) for p in problems]
    )


async def get_custom_problem_handler(
    custom_problem_id: str = Path(..., description="Custom Problem ID"),
    current_user: UserWithPermissions = Depends(require_organizer),
    service: CustomProblemService = Depends(get_custom_problem_service),
) -> CustomProblemResponse:
    """Get a single custom problem owned by the requesting organizer."""
    problem = await service.get_owned(current_user.user_id, custom_problem_id)
    return CustomProblemResponse(
        data=CustomProblemResponseData.model_validate(problem)
    )


async def update_custom_problem_handler(
    custom_problem_id: str = Path(..., description="Custom Problem ID"),
    request: CustomProblemUpdateRequest = Body(...),
    current_user: UserWithPermissions = Depends(require_organizer),
    service: CustomProblemService = Depends(get_custom_problem_service),
) -> CustomProblemResponse:
    """Update an owned custom problem. Slug regenerates only on title change."""
    updated = await service.update(
        user_id=current_user.user_id,
        custom_problem_id=custom_problem_id,
        data=request.data,
    )
    return CustomProblemResponse(
        data=CustomProblemResponseData.model_validate(updated)
    )


async def delete_custom_problem_handler(
    custom_problem_id: str = Path(..., description="Custom Problem ID"),
    current_user: UserWithPermissions = Depends(require_organizer),
    service: CustomProblemService = Depends(get_custom_problem_service),
) -> APIResponse[dict]:
    """Hard-delete an owned custom problem.

    Returns 409 ``CUSTOM_PROBLEM_HAS_CONTEST_REFERENCES`` if the problem is
    still attached to one or more contests.
    """
    await service.delete(current_user.user_id, custom_problem_id)
    return APIResponse[dict](data={"id": custom_problem_id})
