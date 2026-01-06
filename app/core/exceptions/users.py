"""User domain exceptions."""

from typing import Optional

from app.core.exceptions.base import AppException


class UserNotFoundException(AppException):
    """
    Raised when a user is not found.

    HTTP Status: 404 Not Found
    Error Code: USER_NOT_FOUND

    Example:
        raise UserNotFoundException(user_id="123")
    """

    def __init__(self, user_id: Optional[str] = None, message: Optional[str] = None):
        details = {"user_id": user_id} if user_id else None
        super().__init__(
            code="USER_NOT_FOUND",
            message=(
                message or f"User with ID '{user_id}' not found"
                if user_id
                else "User not found"
            ),
            status_code=404,
            details=details,
        )


class UserAlreadyExistsException(AppException):
    """
    Raised when attempting to create a user that already exists.

    HTTP Status: 409 Conflict
    Error Code: USER_ALREADY_EXISTS

    Example:
        raise UserAlreadyExistsException(email="user@example.com")
    """

    def __init__(self, email: Optional[str] = None, message: Optional[str] = None):

        details = {"email": email} if email else None
        super().__init__(
            code="USER_ALREADY_EXISTS",
            message=(
                message or f"User with email '{email}' already exists"
                if email
                else "User already exists"
            ),
            status_code=409,
            details=details,
        )


class UserValidationException(AppException):
    """
    Raised when user data validation fails.

    HTTP Status: 400 Bad Request
    Error Code: USER_VALIDATION_ERROR

    Example:
        raise UserValidationException(
            message="Invalid email format",
            details={"field": "email", "value": "invalid"}
        )
    """

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            code="USER_VALIDATION_ERROR",
            message=message,
            status_code=400,
            details=details,
        )
