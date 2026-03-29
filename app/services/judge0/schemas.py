# app/services/judge0/schemas.py
"""Pydantic models for Judge0 API request/response payloads."""

from pydantic import BaseModel


class Judge0SubmissionRequest(BaseModel):
    """Payload sent to Judge0 POST /submissions."""

    source_code: str          # base64 encoded
    language_id: int
    stdin: str | None = None  # base64 encoded
    expected_output: str | None = None  # base64 encoded
    cpu_time_limit: float | None = None  # seconds
    cpu_extra_time: float | None = None  # seconds
    wall_time_limit: float | None = None  # seconds
    memory_limit: float | None = None  # KB
    redirect_stderr_to_stdout: bool = False


class Judge0Status(BaseModel):
    """Status object embedded in Judge0 submission results."""

    id: int
    description: str


class Judge0SubmissionResult(BaseModel):
    """Response from Judge0 GET /submissions/{token}."""

    token: str
    status: Judge0Status
    stdout: str | None = None       # base64 encoded
    stderr: str | None = None       # base64 encoded
    compile_output: str | None = None  # base64 encoded
    message: str | None = None
    time: float | None = None       # seconds
    wall_time: float | None = None  # seconds
    memory: float | None = None     # KB
    exit_code: int | None = None
    exit_signal: int | None = None


class Judge0Language(BaseModel):
    """Language entry from Judge0 GET /languages."""

    id: int
    name: str
