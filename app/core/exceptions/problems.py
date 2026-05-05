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


class BuiltinProblemNotFoundException(AppException):
    """Raised when a built-in problem is not found. HTTP 404."""

    def __init__(
        self,
        builtin_problem_id: Optional[str] = None,
        message: Optional[str] = None,
    ):
        details = (
            {"builtin_problem_id": builtin_problem_id} if builtin_problem_id else None
        )
        super().__init__(
            code="BUILTIN_PROBLEM_NOT_FOUND",
            message=message
            or (
                f"Built-in problem with ID '{builtin_problem_id}' not found"
                if builtin_problem_id
                else "Built-in problem not found"
            ),
            status_code=404,
            details=details,
        )


class ContestProblemNotFoundException(AppException):
    """Raised when a contest problem is not found. HTTP 404."""

    def __init__(
        self,
        contest_problem_id: Optional[str] = None,
        message: Optional[str] = None,
    ):
        details = (
            {"contest_problem_id": contest_problem_id} if contest_problem_id else None
        )
        super().__init__(
            code="CONTEST_PROBLEM_NOT_FOUND",
            message=message
            or (
                f"Contest problem with ID '{contest_problem_id}' not found"
                if contest_problem_id
                else "Contest problem not found"
            ),
            status_code=404,
            details=details,
        )


class TestCasesNotFoundException(AppException):
    """Raised when test cases have not been uploaded for a problem. HTTP 404."""

    def __init__(self, problem_id: Optional[str] = None):
        details = {"problem_id": problem_id} if problem_id else None
        super().__init__(
            code="TEST_CASES_NOT_FOUND",
            message=f"No test cases found for problem '{problem_id}'"
            if problem_id
            else "No test cases found for this problem",
            status_code=404,
            details=details,
        )


class NotContestOrganizerException(AppException):
    """Raised when a non-organizer tries to modify contest problems. HTTP 403."""

    def __init__(self, message: Optional[str] = None):
        super().__init__(
            code="NOT_CONTEST_ORGANIZER",
            message=message or "Only the contest organizer can perform this action",
            status_code=403,
        )


class CustomProblemNotFoundException(AppException):
    """Raised when a custom (admin-authored) problem is not found. HTTP 404."""

    def __init__(
        self,
        custom_problem_id: Optional[str] = None,
        message: Optional[str] = None,
    ):
        details = (
            {"custom_problem_id": custom_problem_id} if custom_problem_id else None
        )
        super().__init__(
            code="CUSTOM_PROBLEM_NOT_FOUND",
            message=message
            or (
                f"Custom problem with ID '{custom_problem_id}' not found"
                if custom_problem_id
                else "Custom problem not found"
            ),
            status_code=404,
            details=details,
        )


class CustomProblemAccessDeniedException(AppException):
    """Raised when an organizer touches a custom problem they do not own. HTTP 403."""

    def __init__(
        self,
        custom_problem_id: Optional[str] = None,
        message: Optional[str] = None,
    ):
        details = (
            {"custom_problem_id": custom_problem_id} if custom_problem_id else None
        )
        super().__init__(
            code="CUSTOM_PROBLEM_ACCESS_DENIED",
            message=message or "You do not have access to this custom problem",
            status_code=403,
            details=details,
        )


class CustomProblemHasContestReferencesException(AppException):
    """Raised when deleting a custom problem still attached to one or more contests.

    HTTP 409. Returns the blocking contest IDs in ``details.contest_ids``.
    """

    def __init__(self, contest_ids: list[str]):
        super().__init__(
            code="CUSTOM_PROBLEM_HAS_CONTEST_REFERENCES",
            message=(
                "Cannot delete this problem because it is still attached to one "
                "or more contests. Remove it from those contests first."
            ),
            status_code=409,
            details={"contest_ids": contest_ids},
        )


class CustomProblemSlugConflictException(AppException):
    """Raised when an owner-scoped slug cannot be made unique. HTTP 409."""

    def __init__(self, slug: Optional[str] = None):
        details = {"slug": slug} if slug else None
        super().__init__(
            code="CUSTOM_PROBLEM_SLUG_CONFLICT",
            message="Could not generate a unique slug for this problem. Try a different title.",
            status_code=409,
            details=details,
        )


class BuiltinProblemSlugConflictException(AppException):
    """Raised when a globally-unique slug cannot be generated for a built-in problem. HTTP 409."""

    def __init__(self, slug: Optional[str] = None):
        details = {"slug": slug} if slug else None
        super().__init__(
            code="BUILTIN_PROBLEM_SLUG_CONFLICT",
            message="Could not generate a unique slug for this problem. Try a different title.",
            status_code=409,
            details=details,
        )
