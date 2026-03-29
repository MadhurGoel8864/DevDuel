"""Problems API Schemas"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.enums import Difficulty
from app.core.responses import APIResponse


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Request Schemas ────────────────────────────────────────────────────────────


class ImportBuiltinProblemData(BaseSchema):
    builtin_problem_id: str
    problem_order: Optional[int] = None

    @field_validator("problem_order")
    @classmethod
    def order_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("problem_order must be >= 1")
        return v


class ImportBuiltinProblemRequest(BaseSchema):
    data: ImportBuiltinProblemData


class ContestProblemUpdateData(BaseSchema):
    difficulty: Optional[Difficulty] = None
    points: Optional[int] = None
    base_price: Optional[int] = None
    time_limit_ms: Optional[int] = None
    memory_limit_mb: Optional[int] = None
    problem_order: Optional[int] = None

    @field_validator("points")
    @classmethod
    def points_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("points must be >= 1")
        return v

    @field_validator("base_price")
    @classmethod
    def base_price_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("base_price must be >= 1")
        return v

    @field_validator("time_limit_ms")
    @classmethod
    def time_limit_valid(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 100:
            raise ValueError("time_limit_ms must be >= 100")
        return v

    @field_validator("memory_limit_mb")
    @classmethod
    def memory_limit_valid(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 16:
            raise ValueError("memory_limit_mb must be >= 16")
        return v

    @field_validator("problem_order")
    @classmethod
    def order_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("problem_order must be >= 1")
        return v


class ContestProblemUpdateRequest(BaseSchema):
    data: ContestProblemUpdateData


# ── Response Schemas ───────────────────────────────────────────────────────────


class BuiltinProblemResponseData(BaseSchema):
    """Response schema for a single built-in (platform-curated) problem."""

    id: str
    title: str
    slug: str
    description: str
    difficulty: Difficulty
    points: int
    base_price: int
    time_limit_ms: int
    memory_limit_mb: int
    test_cases_url: Optional[str] = None
    created_by: Optional[str] = "system"
    is_active: bool
    created_at: datetime


class ContestProblemResponseData(BaseSchema):
    id: str
    contest_id: str
    problem_id: str
    problem_order: int
    difficulty: Difficulty
    points: int
    base_price: int
    time_limit_ms: int
    memory_limit_mb: int
    test_cases_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    problem: Optional[BuiltinProblemResponseData] = None


# ── Final Response Aliases ─────────────────────────────────────────────────────

BuiltinProblemResponse = APIResponse[BuiltinProblemResponseData]
BuiltinProblemListResponse = APIResponse[list[BuiltinProblemResponseData]]
ContestProblemResponse = APIResponse[ContestProblemResponseData]
ContestProblemListResponse = APIResponse[list[ContestProblemResponseData]]
