"""Contest domain exceptions."""

from typing import Optional

from app.core.exceptions.base import AppException


class ContestNotFoundException(AppException):
    """Raised when a contest is not found. HTTP 404."""

    def __init__(self, contest_id: Optional[str] = None, message: Optional[str] = None):
        details = {"contest_id": contest_id} if contest_id else None
        super().__init__(
            code="CONTEST_NOT_FOUND",
            message=message
            or (
                f"Contest with ID '{contest_id}' not found"
                if contest_id
                else "Contest not found"
            ),
            status_code=404,
            details=details,
        )


class ContestAlreadyRegisteredException(AppException):
    """Raised when a team is already registered for a contest. HTTP 409."""

    def __init__(self, team_id: Optional[str] = None, contest_id: Optional[str] = None):
        details = {"team_id": team_id, "contest_id": contest_id}
        super().__init__(
            code="CONTEST_ALREADY_REGISTERED",
            message="This team is already registered for the contest",
            status_code=409,
            details=details,
        )


class ContestNotActiveException(AppException):
    """Raised when trying to register for an inactive contest. HTTP 400."""

    def __init__(self, contest_id: Optional[str] = None):
        details = {"contest_id": contest_id} if contest_id else None
        super().__init__(
            code="CONTEST_NOT_ACTIVE",
            message="Cannot register for an inactive contest",
            status_code=400,
            details=details,
        )
