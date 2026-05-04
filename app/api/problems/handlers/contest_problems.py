"""Contest Problems Handler Layer"""

import logging
from typing import Any

from fastapi import Body, Depends, Path

from app.api.auth.dependencies import get_current_user
from app.api.auth.schemas import UserWithPermissions
from app.api.problems.schemas.problems import (
    BuiltinProblemResponseData,
    ContestProblemListResponse,
    ContestProblemResponse,
    ContestProblemResponseData,
    ContestProblemUpdateRequest,
    CustomProblemResponseData,
    ImportProblemRequest,
)
from app.api.problems.services.problems import (
    ContestProblemService,
    get_contest_problem_service,
)
from app.core.enums import ProblemKind
from app.database.models.problems import ContestProblem

logger = logging.getLogger(__name__)


def _serialize_resolved_problem(cp: ContestProblem) -> dict[str, Any] | None:
    """Build the unified ``problem`` payload for a ContestProblem response.

    Shape varies by ``problem_kind`` — frontend disambiguates using that field.
    Returns None if the relationship is not loaded (defensive).
    """
    resolved = cp.resolved_problem
    if resolved is None:
        return None
    if cp.problem_kind == ProblemKind.BUILTIN:
        return BuiltinProblemResponseData.model_validate(resolved).model_dump(
            mode="json"
        )
    return CustomProblemResponseData.model_validate(resolved).model_dump(mode="json")


def _to_response_data(cp: ContestProblem) -> ContestProblemResponseData:
    data = ContestProblemResponseData.model_validate(cp)
    data.problem = _serialize_resolved_problem(cp)
    return data


async def import_problem_handler(
    contest_id: str = Path(..., description="Contest ID"),
    request: ImportProblemRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    cp_service: ContestProblemService = Depends(get_contest_problem_service),
) -> ContestProblemResponse:
    """Import either a built-in or a custom problem into a contest.

    The request body must include exactly one of ``builtin_problem_id`` or
    ``custom_problem_id`` (enforced by ImportProblemData.exactly_one_id).
    Custom problems can only be imported by their owner.
    """
    cp = await cp_service.import_problem_to_contest(
        contest_id=contest_id,
        requesting_user_id=current_user.user_id,
        data=request.data,
    )
    logger.info(
        f"Problem imported into contest {contest_id} by {current_user.user_id}: "
        f"kind={cp.problem_kind.value} cp_id={cp.id}"
    )
    return ContestProblemResponse(data=_to_response_data(cp))


async def list_contest_problems_handler(
    contest_id: str = Path(..., description="Contest ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    cp_service: ContestProblemService = Depends(get_contest_problem_service),
) -> ContestProblemListResponse:
    """List all active problems in a contest, sorted by problem_order."""
    cps = await cp_service.list_contest_problems(contest_id)
    return ContestProblemListResponse(data=[_to_response_data(cp) for cp in cps])


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
    logger.info(
        f"ContestProblem {contest_problem_id} removed from contest {contest_id} "
        f"by {current_user.user_id}"
    )
    return ContestProblemResponse(data=_to_response_data(cp))


async def update_contest_problem_handler(
    contest_id: str = Path(..., description="Contest ID"),
    contest_problem_id: str = Path(..., description="ContestProblem ID"),
    request: ContestProblemUpdateRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    cp_service: ContestProblemService = Depends(get_contest_problem_service),
) -> ContestProblemResponse:
    """Update contest-specific overrides for a problem.

    Organizer can change difficulty, points, base_price, time_limit_ms,
    memory_limit_mb, and problem_order. The underlying problem fields
    (title/description/etc.) cannot be changed here — for custom problems,
    edit the source problem via /problems/custom/{id} instead.
    """
    update_data = request.data.model_dump(exclude_none=True)
    cp = await cp_service.update_contest_problem(
        contest_id=contest_id,
        contest_problem_id=contest_problem_id,
        requesting_user_id=current_user.user_id,
        **update_data,
    )
    logger.info(
        f"ContestProblem {contest_problem_id} updated in contest {contest_id} "
        f"by {current_user.user_id}"
    )
    return ContestProblemResponse(data=_to_response_data(cp))
