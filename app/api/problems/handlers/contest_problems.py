"""Contest Problems Handler Layer"""

import logging

from fastapi import Body, Depends, Path

from app.api.auth.dependencies import get_current_user
from app.api.auth.schemas import UserWithPermissions
from app.api.problems.schemas.problems import (
    BuiltinProblemResponseData,
    ContestProblemListResponse,
    ContestProblemResponse,
    ContestProblemResponseData,
    ContestProblemUpdateRequest,
    ImportBuiltinProblemRequest,
)
from app.api.problems.services.problems import (
    ContestProblemService,
    get_contest_problem_service,
)

logger = logging.getLogger(__name__)


async def import_builtin_problem_handler(
    contest_id: str = Path(..., description="Contest ID"),
    request: ImportBuiltinProblemRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    cp_service: ContestProblemService = Depends(get_contest_problem_service),
) -> ContestProblemResponse:
    """Import a built-in problem into a contest.

    Creates a contest_problems row referencing the builtin problem directly,
    inheriting its default values for difficulty/points/base_price/time_limit/memory_limit.
    """
    cp = await cp_service.import_builtin_problem_to_contest(
        builtin_problem_id=request.data.builtin_problem_id,
        contest_id=contest_id,
        requesting_user_id=current_user.user_id,
        problem_order=request.data.problem_order,
    )
    data = ContestProblemResponseData.model_validate(cp)
    if cp.problem:
        data.problem = BuiltinProblemResponseData.model_validate(cp.problem)
    logger.info(
        f"Builtin problem {request.data.builtin_problem_id} imported into "
        f"contest {contest_id} by {current_user.user_id}"
    )
    return ContestProblemResponse(data=data)


async def list_contest_problems_handler(
    contest_id: str = Path(..., description="Contest ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    cp_service: ContestProblemService = Depends(get_contest_problem_service),
) -> ContestProblemListResponse:
    """List all active problems in a contest, sorted by problem_order."""
    cps = await cp_service.list_contest_problems(contest_id)
    response_items = []
    for cp in cps:
        item = ContestProblemResponseData.model_validate(cp)
        if cp.problem:
            item.problem = BuiltinProblemResponseData.model_validate(cp.problem)
        response_items.append(item)
    return ContestProblemListResponse(data=response_items)


async def remove_problem_from_contest_handler(
    contest_id: str = Path(..., description="Contest ID"),
    contest_problem_id: str = Path(..., description="ContestProblem ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    cp_service: ContestProblemService = Depends(get_contest_problem_service),
) -> ContestProblemResponse:
    """Hard-delete a ContestProblem row from the contest."""
    cp = await cp_service.remove_problem_from_contest(
        contest_id=contest_id,
        contest_problem_id=contest_problem_id,
        requesting_user_id=current_user.user_id,
    )
    data = ContestProblemResponseData.model_validate(cp)
    if cp.problem:
        data.problem = BuiltinProblemResponseData.model_validate(cp.problem)
    logger.info(
        f"ContestProblem {contest_problem_id} removed from contest {contest_id} "
        f"by {current_user.user_id}"
    )
    return ContestProblemResponse(data=data)


async def update_contest_problem_handler(
    contest_id: str = Path(..., description="Contest ID"),
    contest_problem_id: str = Path(..., description="ContestProblem ID"),
    request: ContestProblemUpdateRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    cp_service: ContestProblemService = Depends(get_contest_problem_service),
) -> ContestProblemResponse:
    """Update contest-specific overrides for a problem.

    Organizer can change difficulty, points, base_price, time_limit_ms,
    memory_limit_mb, and problem_order. Title, slug, description cannot be changed.
    """
    update_data = request.data.model_dump(exclude_none=True)
    cp = await cp_service.update_contest_problem(
        contest_id=contest_id,
        contest_problem_id=contest_problem_id,
        requesting_user_id=current_user.user_id,
        **update_data,
    )
    data = ContestProblemResponseData.model_validate(cp)
    if cp.problem:
        data.problem = BuiltinProblemResponseData.model_validate(cp.problem)
    logger.info(
        f"ContestProblem {contest_problem_id} updated in contest {contest_id} "
        f"by {current_user.user_id}"
    )
    return ContestProblemResponse(data=data)
