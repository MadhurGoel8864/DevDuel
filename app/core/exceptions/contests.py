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


class RegistrationClosedException(AppException):
    """Raised when a team tries to register for a contest that is not open. HTTP 400."""

    def __init__(self, contest_id: Optional[str] = None):
        details = {"contest_id": contest_id} if contest_id else None
        super().__init__(
            code="REGISTRATION_CLOSED",
            message="Registration is not open for this contest",
            status_code=400,
            details=details,
        )


class InvalidContestStateTransition(AppException):
    """Raised when an invalid contest lifecycle transition is attempted. HTTP 409."""

    def __init__(
        self,
        from_status: Optional[str] = None,
        to_status: Optional[str] = None,
    ):
        details: Optional[dict] = None
        if from_status and to_status:
            details = {"from": from_status, "to": to_status}
        super().__init__(
            code="INVALID_CONTEST_STATE_TRANSITION",
            message=(
                f"Cannot transition contest from '{from_status}' to '{to_status}'"
                if from_status and to_status
                else "Invalid contest state transition"
            ),
            status_code=409,
            details=details,
        )
