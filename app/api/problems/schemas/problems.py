"""Problems API Schemas"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.enums import Difficulty
from app.core.responses import APIResponse
from app.core.timezone_utils import ISTDatetimeMixin


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Request Schemas ────────────────────────────────────────────────────────────


class ProblemCreateData(BaseSchema):
    title: str
    description: str
    difficulty: Difficulty
    points: int
    base_price: int
    time_limit_ms: Optional[int] = 2000
    memory_limit_mb: Optional[int] = 256

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title must not be empty")
        return v.strip()

    @field_validator("points")
    @classmethod
    def points_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("points must be greater than 0")
        return v

    @field_validator("base_price")
    @classmethod
    def base_price_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("base_price must be greater than 0")
        return v


class ProblemCreateRequest(BaseSchema):
    data: ProblemCreateData


class ProblemUpdateData(BaseSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    points: Optional[int] = None
    base_price: Optional[int] = None
    time_limit_ms: Optional[int] = None
    memory_limit_mb: Optional[int] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("title must not be empty")
        return v.strip() if v else v

    @field_validator("points")
    @classmethod
    def points_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("points must be greater than 0")
        return v

    @field_validator("base_price")
    @classmethod
    def base_price_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("base_price must be greater than 0")
        return v


class ProblemUpdateRequest(BaseSchema):
    data: ProblemUpdateData


class ContestProblemCreateData(BaseSchema):
    problem_id: str
    problem_order: int

    @field_validator("problem_order")
    @classmethod
    def order_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("problem_order must be >= 1")
        return v


class ContestProblemCreateRequest(BaseSchema):
    data: ContestProblemCreateData


# ── Response Schemas ───────────────────────────────────────────────────────────


class ProblemResponseData(BaseSchema, ISTDatetimeMixin):
    id: str
    title: str
    slug: str
    description: str
    difficulty: Difficulty
    points: int
    base_price: int
    time_limit_ms: int
    memory_limit_mb: int
    created_by: str
    is_active: bool
    created_at: datetime


class ContestProblemResponseData(BaseSchema, ISTDatetimeMixin):
    id: str
    contest_id: str
    problem_id: str
    problem_order: int
    is_active: bool
    created_at: datetime
    problem: Optional[ProblemResponseData] = None


# ── Final Response Aliases ─────────────────────────────────────────────────────

ProblemResponse = APIResponse[ProblemResponseData]
ProblemListResponse = APIResponse[list[ProblemResponseData]]
ContestProblemResponse = APIResponse[ContestProblemResponseData]
ContestProblemListResponse = APIResponse[list[ContestProblemResponseData]]


class BuiltinProblemResponseData(BaseSchema, ISTDatetimeMixin):
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
    created_at: datetime


class ImportBuiltinProblemData(BaseSchema):
    builtin_problem_id: str
    problem_order: int

    @field_validator("problem_order")
    @classmethod
    def order_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("problem_order must be >= 1")
        return v


class ImportBuiltinProblemRequest(BaseSchema):
    data: ImportBuiltinProblemData


BuiltinProblemListResponse = APIResponse[list[BuiltinProblemResponseData]]
