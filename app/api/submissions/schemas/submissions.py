"""Submissions API Pydantic Schemas"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.enums import SubmissionVerdict
from app.core.responses import APIResponse


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Request Schemas ────────────────────────────────────────────────────────────


class SubmitCodeData(BaseSchema):
    """Payload for submitting code."""

    team_id: str
    language: str  # "python", "cpp", etc.
    source_code: str

    @field_validator("source_code")
    @classmethod
    def source_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source_code cannot be empty")
        return v


class SubmitCodeRequest(BaseSchema):
    data: SubmitCodeData


# ── Response Schemas ───────────────────────────────────────────────────────────


class TestResultResponseData(BaseSchema):
    """Per-test-case result."""

    test_case_index: int
    verdict: str
    time_ms: Optional[int] = None
    memory_kb: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    compile_output: Optional[str] = None
    is_sample: bool = False
    input: Optional[str] = None
    expected_output: Optional[str] = None


class SubmissionResponseData(BaseSchema):
    """Full submission details."""

    id: str
    contest_id: str
    contest_problem_id: str
    assignment_id: str
    team_id: str
    user_id: Optional[str] = None
    language: str
    language_id: int
    verdict: SubmissionVerdict
    passed_test_cases: int
    total_test_cases: int
    max_time_ms: Optional[int] = None
    max_memory_kb: Optional[int] = None
    compile_output: Optional[str] = None
    stderr: Optional[str] = None
    error_message: Optional[str] = None
    submitted_at: datetime
    judged_at: Optional[datetime] = None


class SubmissionDetailResponseData(SubmissionResponseData):
    """Submission with per-test-case results."""

    test_results: list[TestResultResponseData] = []


class SubmissionListItem(BaseSchema):
    """Lightweight submission for list views."""

    id: str
    contest_problem_id: str
    language: str
    verdict: SubmissionVerdict
    passed_test_cases: int
    total_test_cases: int
    max_time_ms: Optional[int] = None
    max_memory_kb: Optional[int] = None
    submitted_at: datetime


# ── Response Aliases ──────────────────────────────────────────────────────────

SubmissionResponse = APIResponse[SubmissionResponseData]
SubmissionDetailResponse = APIResponse[SubmissionDetailResponseData]
SubmissionListResponse = APIResponse[list[SubmissionListItem]]
