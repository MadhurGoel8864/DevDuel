"""Problem domain exceptions."""

from typing import Optional

from app.core.exceptions.base import AppException


class ProblemNotFoundException(AppException):
    """Raised when a problem is not found. HTTP 404."""

    def __init__(self, problem_id: Optional[str] = None, message: Optional[str] = None):
        details = {"problem_id": problem_id} if problem_id else None
        super().__init__(
            code="PROBLEM_NOT_FOUND",
            message=message
            or (
                f"Problem with ID '{problem_id}' not found"
                if problem_id
                else "Problem not found"
            ),
            status_code=404,
            details=details,
        )


class ProblemAlreadyInContestException(AppException):
    """Raised when a problem is already attached to a contest. HTTP 409."""

    def __init__(
        self,
        problem_id: Optional[str] = None,
        contest_id: Optional[str] = None,
    ):
        details = {"problem_id": problem_id, "contest_id": contest_id}
        super().__init__(
            code="PROBLEM_ALREADY_IN_CONTEST",
            message="This problem is already attached to the contest",
            status_code=409,
            details=details,
        )


class InvalidProblemOrderException(AppException):
    """Raised when the problem_order value is invalid or conflicts. HTTP 400."""

    def __init__(self, message: Optional[str] = None):
        super().__init__(
            code="INVALID_PROBLEM_ORDER",
            message=message or "Invalid problem order",
            status_code=400,
        )
