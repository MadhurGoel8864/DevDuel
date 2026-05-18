"""Problems API Schemas"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.enums import Difficulty, ProblemKind
from app.core.responses import APIResponse


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Built-in problem responses (unchanged surface) ────────────────────────────


class BuiltinProblemResponseData(BaseSchema):
    """Response schema for a single built-in (platform-curated) problem."""

    id: str
    title: str
    slug: str
    description: str
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    constraints: Optional[str] = None
    difficulty: Difficulty
    points: int
    base_price: int
    time_limit_ms: int
    memory_limit_mb: int
    test_cases_url: Optional[str] = None
    created_by: Optional[str] = "system"
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Built-in problem write schemas ───────────────────────────────────────────


def _validate_points(v: Optional[int]) -> Optional[int]:
    if v is not None and v < 1:
        raise ValueError("points must be >= 1")
    return v


def _validate_base_price(v: Optional[int]) -> Optional[int]:
    if v is not None and v < 1:
        raise ValueError("base_price must be >= 1")
    return v


def _validate_time_limit(v: Optional[int]) -> Optional[int]:
    if v is not None and v < 100:
        raise ValueError("time_limit_ms must be >= 100")
    return v


def _validate_memory_limit(v: Optional[int]) -> Optional[int]:
    if v is not None and v < 16:
        raise ValueError("memory_limit_mb must be >= 16")
    return v


class BuiltinProblemCreateData(BaseSchema):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    input_format: Optional[str] = Field(default=None, min_length=1)
    output_format: Optional[str] = Field(default=None, min_length=1)
    constraints: Optional[str] = Field(default=None, min_length=1)
    difficulty: Difficulty
    points: int
    base_price: int
    time_limit_ms: int = 2000
    memory_limit_mb: int = 256

    _v_points = field_validator("points")(_validate_points)
    _v_base_price = field_validator("base_price")(_validate_base_price)
    _v_time_limit = field_validator("time_limit_ms")(_validate_time_limit)
    _v_memory = field_validator("memory_limit_mb")(_validate_memory_limit)


class BuiltinProblemCreateRequest(BaseSchema):
    data: BuiltinProblemCreateData


class BuiltinProblemUpdateData(BaseSchema):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, min_length=1)
    input_format: Optional[str] = Field(default=None, min_length=1)
    output_format: Optional[str] = Field(default=None, min_length=1)
    constraints: Optional[str] = Field(default=None, min_length=1)
    difficulty: Optional[Difficulty] = None
    points: Optional[int] = None
    base_price: Optional[int] = None
    time_limit_ms: Optional[int] = None
    memory_limit_mb: Optional[int] = None

    _v_points = field_validator("points")(_validate_points)
    _v_base_price = field_validator("base_price")(_validate_base_price)
    _v_time_limit = field_validator("time_limit_ms")(_validate_time_limit)
    _v_memory = field_validator("memory_limit_mb")(_validate_memory_limit)


class BuiltinProblemUpdateRequest(BaseSchema):
    data: BuiltinProblemUpdateData


# ── Custom problem schemas ────────────────────────────────────────────────────


class CustomProblemCreateData(BaseSchema):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    input_format: str = Field(..., min_length=1)
    output_format: str = Field(..., min_length=1)
    constraints: str = Field(..., min_length=1)
    difficulty: Difficulty
    points: int
    base_price: int
    time_limit_ms: int = 2000
    memory_limit_mb: int = 256

    _v_points = field_validator("points")(_validate_points)
    _v_base_price = field_validator("base_price")(_validate_base_price)
    _v_time_limit = field_validator("time_limit_ms")(_validate_time_limit)
    _v_memory = field_validator("memory_limit_mb")(_validate_memory_limit)


class CustomProblemCreateRequest(BaseSchema):
    data: CustomProblemCreateData


class CustomProblemUpdateData(BaseSchema):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, min_length=1)
    input_format: Optional[str] = Field(default=None, min_length=1)
    output_format: Optional[str] = Field(default=None, min_length=1)
    constraints: Optional[str] = Field(default=None, min_length=1)
    difficulty: Optional[Difficulty] = None
    points: Optional[int] = None
    base_price: Optional[int] = None
    time_limit_ms: Optional[int] = None
    memory_limit_mb: Optional[int] = None

    _v_points = field_validator("points")(_validate_points)
    _v_base_price = field_validator("base_price")(_validate_base_price)
    _v_time_limit = field_validator("time_limit_ms")(_validate_time_limit)
    _v_memory = field_validator("memory_limit_mb")(_validate_memory_limit)


class CustomProblemUpdateRequest(BaseSchema):
    data: CustomProblemUpdateData


class CustomProblemResponseData(BaseSchema):
    """Response schema for an admin-authored problem."""

    id: str
    created_by: str
    title: str
    slug: str
    description: str
    input_format: str
    output_format: str
    constraints: str
    difficulty: Difficulty
    points: int
    base_price: int
    time_limit_ms: int
    memory_limit_mb: int
    is_active: bool
    test_cases_url: Optional[str] = None
    validation_status: str = "UNVALIDATED"
    validated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ── Problem validation schemas ────────────────────────────────────────────────


class ValidateProblemData(BaseSchema):
    language: str = Field(..., min_length=1, max_length=50)
    source_code: str = Field(..., min_length=1)


class ValidateProblemRequest(BaseSchema):
    data: ValidateProblemData


class ValidationTestResult(BaseSchema):
    index: int
    is_sample: bool
    passed: bool
    verdict: str
    input: str
    expected_output: str
    actual_output: Optional[str] = None
    time_ms: Optional[int] = None
    memory_kb: Optional[int] = None
    stderr: Optional[str] = None
    compile_output: Optional[str] = None


class ValidateProblemResponseData(BaseSchema):
    problem_id: str
    validation_status: str
    passed: int
    total: int
    test_results: list[ValidationTestResult]


ValidateProblemResponse = APIResponse[ValidateProblemResponseData]


class ProbeResultResponseData(BaseSchema):
    problem_id: str
    passed: int
    total: int
    test_results: list[ValidationTestResult]


ProbeResultResponse = APIResponse[ProbeResultResponseData]


# ── Contest problem schemas ────────────────────────────────────────────────────


class ImportProblemData(BaseSchema):
    builtin_problem_id: Optional[str] = None
    custom_problem_id: Optional[str] = None
    problem_order: Optional[int] = None

    @field_validator("problem_order")
    @classmethod
    def order_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("problem_order must be >= 1")
        return v

    @model_validator(mode="after")
    def exactly_one_id(self) -> "ImportProblemData":
        ids_set = sum(
            1
            for v in (self.builtin_problem_id, self.custom_problem_id)
            if v is not None
        )
        if ids_set != 1:
            raise ValueError(
                "Exactly one of builtin_problem_id or custom_problem_id must be provided"
            )
        return self


class ImportProblemRequest(BaseSchema):
    data: ImportProblemData


class ContestProblemUpdateData(BaseSchema):
    difficulty: Optional[Difficulty] = None
    points: Optional[int] = None
    base_price: Optional[int] = None
    time_limit_ms: Optional[int] = None
    memory_limit_mb: Optional[int] = None
    problem_order: Optional[int] = None

    _v_points = field_validator("points")(_validate_points)
    _v_base_price = field_validator("base_price")(_validate_base_price)
    _v_time_limit = field_validator("time_limit_ms")(_validate_time_limit)
    _v_memory = field_validator("memory_limit_mb")(_validate_memory_limit)

    @field_validator("problem_order")
    @classmethod
    def order_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("problem_order must be >= 1")
        return v


class ContestProblemUpdateRequest(BaseSchema):
    data: ContestProblemUpdateData


class ContestProblemResponseData(BaseSchema):
    id: str
    contest_id: str
    problem_kind: ProblemKind
    builtin_problem_id: Optional[str] = None
    custom_problem_id: Optional[str] = None
    problem_order: int
    difficulty: Difficulty
    points: int
    base_price: int
    time_limit_ms: int
    memory_limit_mb: int
    is_active: bool
    created_at: datetime
    # Unified problem payload — shape varies by problem_kind. Frontend
    # disambiguates on `problem_kind`.
    problem: Optional[dict[str, Any]] = None


# ── Final Response Aliases ─────────────────────────────────────────────────────

BuiltinProblemResponse = APIResponse[BuiltinProblemResponseData]
BuiltinProblemListResponse = APIResponse[list[BuiltinProblemResponseData]]
CustomProblemResponse = APIResponse[CustomProblemResponseData]
CustomProblemListResponse = APIResponse[list[CustomProblemResponseData]]
ContestProblemResponse = APIResponse[ContestProblemResponseData]
ContestProblemListResponse = APIResponse[list[ContestProblemResponseData]]

__all__ = [
    "SampleIOItem",
    "BuiltinProblemResponseData",
    "BuiltinProblemCreateData",
    "BuiltinProblemCreateRequest",
    "BuiltinProblemUpdateData",
    "BuiltinProblemUpdateRequest",
    "BuiltinProblemResponse",
    "BuiltinProblemListResponse",
    "CustomProblemCreateData",
    "CustomProblemCreateRequest",
    "CustomProblemUpdateData",
    "CustomProblemUpdateRequest",
    "CustomProblemResponseData",
    "CustomProblemResponse",
    "CustomProblemListResponse",
    "ValidateProblemData",
    "ValidateProblemRequest",
    "ValidationTestResult",
    "ValidateProblemResponseData",
    "ValidateProblemResponse",
    "ProbeResultResponseData",
    "ProbeResultResponse",
    "ImportProblemData",
    "ImportProblemRequest",
    "ContestProblemUpdateData",
    "ContestProblemUpdateRequest",
    "ContestProblemResponseData",
    "ContestProblemResponse",
    "ContestProblemListResponse",
]
