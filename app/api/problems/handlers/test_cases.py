"""Test Cases Upload Handler"""

import logging
from typing import Optional

from fastapi import Body, Depends, Path
from pydantic import BaseModel, ConfigDict, field_validator

from app.api.auth.dependencies import require_organizer
from app.api.auth.schemas import UserWithPermissions
from app.api.problems.dao.problems import (
    BuiltinProblemDAO,
    get_builtin_problem_dao,
)
from app.core.exceptions.problems import BuiltinProblemNotFoundException
from app.core.responses import APIResponse
from app.services.storage import storage_service

logger = logging.getLogger(__name__)


# ── Schemas (inline — single endpoint, no separate file needed) ───────────────


class TestCaseItem(BaseModel):
    input: str
    expected_output: str
    is_sample: bool = False


class UploadTestCasesData(BaseModel):
    test_cases: list[TestCaseItem]

    @field_validator("test_cases")
    @classmethod
    def at_least_one(cls, v: list[TestCaseItem]) -> list[TestCaseItem]:
        if not v:
            raise ValueError("At least one test case is required")
        return v


class UploadTestCasesRequest(BaseModel):
    data: UploadTestCasesData


class UploadTestCasesResponseData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    problem_id: str
    problem_slug: str
    test_cases_url: str
    total_count: int
    sample_count: int


UploadTestCasesResponse = APIResponse[UploadTestCasesResponseData]


# ── Handler ───────────────────────────────────────────────────────────────────


async def upload_test_cases_handler(
    problem_id: str = Path(..., description="Builtin Problem ID"),
    request: UploadTestCasesRequest = Body(...),
    current_user: UserWithPermissions = Depends(require_organizer),
    dao: BuiltinProblemDAO = Depends(get_builtin_problem_dao),
) -> UploadTestCasesResponse:
    """Upload test cases for a builtin problem. Replaces any existing test cases in GCS."""
    logger.info(
        f"[test_cases] Upload request: problem_id={problem_id}, "
        f"user={current_user.user_id}, count={len(request.data.test_cases)}"
    )

    problem = await dao.get_by_id(problem_id)
    if not problem or not problem.is_active:
        logger.warning(f"[test_cases] Problem not found or inactive: {problem_id}")
        raise BuiltinProblemNotFoundException(builtin_problem_id=problem_id)

    test_cases_raw = [tc.model_dump() for tc in request.data.test_cases]

    logger.debug(
        f"[test_cases] Uploading to GCS for slug='{problem.slug}', "
        f"total={len(test_cases_raw)}, "
        f"samples={sum(1 for tc in test_cases_raw if tc.get('is_sample'))}"
    )
    url = storage_service.upload_test_cases(problem.slug, test_cases_raw)
    logger.info(f"[test_cases] GCS upload complete: {url}")

    # Save URL on the problem
    problem.test_cases_url = url
    dao._session.add(problem)
    await dao._session.commit()
    await dao._session.refresh(problem)

    samples = [tc for tc in test_cases_raw if tc.get("is_sample")]

    logger.info(
        f"[test_cases] Saved test_cases_url on problem '{problem.slug}': "
        f"{len(test_cases_raw)} total, {len(samples)} samples"
    )

    return UploadTestCasesResponse(
        data=UploadTestCasesResponseData(
            problem_id=problem.id,
            problem_slug=problem.slug,
            test_cases_url=url,
            total_count=len(test_cases_raw),
            sample_count=len(samples),
        )
    )
