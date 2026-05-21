"""Test Cases Upload Handler"""

import logging

from fastapi import Body, Depends, Path
from pydantic import BaseModel, ConfigDict, field_validator

from app.api.auth.dependencies import require_admin, require_admin_or_organizer, require_organizer
from app.api.auth.schemas import UserWithPermissions
from app.api.problems.dao.problems import (
    BuiltinProblemDAO,
    get_builtin_problem_dao,
)
from app.api.problems.schemas.problems import (
    ProbeResultResponse,
    ProbeResultResponseData,
    ValidateProblemRequest,
    ValidateProblemResponse,
    ValidateProblemResponseData,
    ValidationTestResult,
)
from app.api.problems.services.problems import (
    BuiltinProblemService,
    CustomProblemService,
    get_builtin_problem_service,
    get_custom_problem_service,
)
from app.api.submissions.services.submissions import judge0_client
from app.core.exceptions.problems import (
    BuiltinProblemNotFoundException,
    TestCasesNotFoundException,
)
from app.core.responses import APIResponse
from app.services.storage import storage_service
from app.services.storage.gcs import StorageError

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


class GetTestCaseItem(BaseModel):
    input: str
    expected_output: str
    is_sample: bool


class GetTestCasesResponseData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    problem_id: str
    problem_title: str
    test_cases: list[GetTestCaseItem]
    total_count: int
    sample_count: int


GetTestCasesResponse = APIResponse[GetTestCasesResponseData]


# ── Handlers ─────────────────────────────────────────────────────────────────


async def upload_test_cases_handler(
    problem_id: str = Path(..., description="Builtin Problem ID"),
    request: UploadTestCasesRequest = Body(...),
    current_user: UserWithPermissions = Depends(require_admin),
    dao: BuiltinProblemDAO = Depends(get_builtin_problem_dao),
) -> UploadTestCasesResponse:
    """Upload test cases for a builtin problem. Replaces any existing test cases in GCS. Requires admin role."""
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


async def upload_custom_test_cases_handler(
    custom_problem_id: str = Path(..., description="Custom Problem ID"),
    request: UploadTestCasesRequest = Body(...),
    current_user: UserWithPermissions = Depends(require_organizer),
    service: CustomProblemService = Depends(get_custom_problem_service),
) -> UploadTestCasesResponse:
    """Upload test cases for a custom (admin-authored) problem.

    Replaces any existing test cases in GCS. Only the problem's owner may upload.
    """
    problem = await service.get_owned(current_user.user_id, custom_problem_id)

    test_cases_raw = [tc.model_dump() for tc in request.data.test_cases]
    logger.info(
        f"[custom_test_cases] Uploading for problem {problem.id} "
        f"(slug='{problem.slug}'), total={len(test_cases_raw)}"
    )
    url = storage_service.upload_custom_test_cases(problem.id, test_cases_raw)
    await service.set_test_cases_url(problem, url)

    samples = [tc for tc in test_cases_raw if tc.get("is_sample")]
    return UploadTestCasesResponse(
        data=UploadTestCasesResponseData(
            problem_id=problem.id,
            problem_slug=problem.slug,
            test_cases_url=url,
            total_count=len(test_cases_raw),
            sample_count=len(samples),
        )
    )


async def get_custom_test_cases_handler(
    custom_problem_id: str = Path(..., description="Custom Problem ID"),
    current_user: UserWithPermissions = Depends(require_organizer),
    service: CustomProblemService = Depends(get_custom_problem_service),
) -> GetTestCasesResponse:
    """Fetch all test cases for a custom problem from GCS. Owner-only."""
    problem = await service.get_owned(current_user.user_id, custom_problem_id)
    if not problem.test_cases_url:
        raise TestCasesNotFoundException(problem_id=problem.id)

    try:
        test_cases_raw = storage_service.download_test_cases_from_url(
            problem.test_cases_url
        )
    except StorageError:
        logger.error(
            f"[custom_test_cases] Failed to download test cases for {problem.id}"
        )
        raise TestCasesNotFoundException(problem_id=problem.id)

    test_cases = [GetTestCaseItem(**tc) for tc in test_cases_raw]
    samples = [tc for tc in test_cases if tc.is_sample]

    return GetTestCasesResponse(
        data=GetTestCasesResponseData(
            problem_id=problem.id,
            problem_title=problem.title,
            test_cases=test_cases,
            total_count=len(test_cases),
            sample_count=len(samples),
        )
    )


async def validate_custom_problem_handler(
    custom_problem_id: str = Path(..., description="Custom Problem ID"),
    request: ValidateProblemRequest = Body(...),
    current_user: UserWithPermissions = Depends(require_organizer),
    service: CustomProblemService = Depends(get_custom_problem_service),
) -> ValidateProblemResponse:
    """Run a reference solution against all test cases to validate a custom problem.

    Sets validation_status=VALID only if every test case passes.
    The problem must be validated before it can be imported into a contest.
    """
    result = await service.validate(
        user_id=current_user.user_id,
        custom_problem_id=custom_problem_id,
        language=request.data.language,
        source_code=request.data.source_code,
        judge0=judge0_client,
    )
    return ValidateProblemResponse(
        data=ValidateProblemResponseData(
            problem_id=result["problem_id"],
            validation_status=result["validation_status"],
            passed=result["passed"],
            total=result["total"],
            test_results=[ValidationTestResult(**tr) for tr in result["test_results"]],
        )
    )


async def probe_custom_problem_handler(
    custom_problem_id: str = Path(..., description="Custom Problem ID"),
    request: ValidateProblemRequest = Body(...),
    current_user: UserWithPermissions = Depends(require_organizer),
    service: CustomProblemService = Depends(get_custom_problem_service),
) -> ProbeResultResponse:
    """Run any solution against all test cases without changing validation_status.

    Use this to calibrate time/memory limits — test optimised and brute-force
    solutions side by side before committing to a reference run via /validate.
    """
    result = await service.probe(
        user_id=current_user.user_id,
        custom_problem_id=custom_problem_id,
        language=request.data.language,
        source_code=request.data.source_code,
        judge0=judge0_client,
    )
    return ProbeResultResponse(
        data=ProbeResultResponseData(
            problem_id=result["problem_id"],
            passed=result["passed"],
            total=result["total"],
            test_results=[ValidationTestResult(**tr) for tr in result["test_results"]],
        )
    )


async def probe_builtin_problem_handler(
    problem_id: str = Path(..., description="Builtin Problem ID"),
    request: ValidateProblemRequest = Body(...),
    current_user: UserWithPermissions = Depends(require_admin_or_organizer),
    service: BuiltinProblemService = Depends(get_builtin_problem_service),
) -> ProbeResultResponse:
    """Run any solution against all test cases for a built-in problem without any DB writes.

    Use this to calibrate time/memory limits — test optimised and brute-force
    solutions to confirm the right ones pass and slow ones TLE. Requires admin role.
    """
    result = await service.probe(
        problem_id=problem_id,
        language=request.data.language,
        source_code=request.data.source_code,
        judge0=judge0_client,
    )
    return ProbeResultResponse(
        data=ProbeResultResponseData(
            problem_id=result["problem_id"],
            passed=result["passed"],
            total=result["total"],
            test_results=[ValidationTestResult(**tr) for tr in result["test_results"]],
        )
    )


async def get_test_cases_handler(
    problem_id: str = Path(..., description="Builtin Problem ID"),
    current_user: UserWithPermissions = Depends(require_organizer),
    dao: BuiltinProblemDAO = Depends(get_builtin_problem_dao),
) -> GetTestCasesResponse:
    """Fetch all test cases for a builtin problem from GCS. Requires organizer role."""
    problem = await dao.get_by_id(problem_id)
    if not problem or not problem.is_active:
        raise BuiltinProblemNotFoundException(builtin_problem_id=problem_id)

    if not problem.test_cases_url:
        raise TestCasesNotFoundException(problem_id=problem_id)

    try:
        test_cases_raw = storage_service.download_test_cases_from_url(
            problem.test_cases_url
        )
    except StorageError:
        logger.error(
            f"[test_cases] Failed to download test cases for problem {problem_id}"
        )
        raise TestCasesNotFoundException(problem_id=problem_id)

    test_cases = [GetTestCaseItem(**tc) for tc in test_cases_raw]
    samples = [tc for tc in test_cases if tc.is_sample]

    return GetTestCasesResponse(
        data=GetTestCasesResponseData(
            problem_id=problem.id,
            problem_title=problem.title,
            test_cases=test_cases,
            total_count=len(test_cases),
            sample_count=len(samples),
        )
    )
