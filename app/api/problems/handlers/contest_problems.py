"""Contest Problems Handler Layer"""

import logging

from fastapi import Body, Depends, Path

from app.api.auth.dependencies import get_current_user
from app.api.auth.schemas import UserWithPermissions
from app.api.problems.schemas.problems import (
    ContestProblemCreateRequest,
    ContestProblemListResponse,
    ContestProblemResponse,
    ContestProblemResponseData,
    ProblemResponseData,
)
from app.api.problems.services.problems import (
    ContestProblemService,
    get_contest_problem_service,
)

logger = logging.getLogger(__name__)


async def add_problem_to_contest_handler(
    contest_id: str = Path(..., description="Contest ID"),
    request: ContestProblemCreateRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    cp_service: ContestProblemService = Depends(get_contest_problem_service),
) -> ContestProblemResponse:
    """Attach a problem to a contest at a specific bidding order."""
    cp = await cp_service.add_problem_to_contest(
        contest_id=contest_id,
        problem_id=request.data.problem_id,
        problem_order=request.data.problem_order,
        requesting_user_id=current_user.user_id,
    )
    return ContestProblemResponse(data=ContestProblemResponseData.model_validate(cp))


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
            item.problem = ProblemResponseData.model_validate(cp.problem)
        response_items.append(item)
    return ContestProblemListResponse(data=response_items)


async def remove_problem_from_contest_handler(
    contest_id: str = Path(..., description="Contest ID"),
    contest_problem_id: str = Path(..., description="ContestProblem ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    cp_service: ContestProblemService = Depends(get_contest_problem_service),
) -> ContestProblemResponse:
    """Soft-delete a ContestProblem (is_active=False)."""
    cp = await cp_service.remove_problem_from_contest(
        contest_id=contest_id,
        contest_problem_id=contest_problem_id,
        requesting_user_id=current_user.user_id,
    )
    logger.info(
        f"ContestProblem {contest_problem_id} removed from contest {contest_id} "
        f"by {current_user.user_id}"
    )
    return ContestProblemResponse(data=ContestProblemResponseData.model_validate(cp))
