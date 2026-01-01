"""Authentication and authorization exceptions."""

from typing import Optional

from app.core.exceptions.base import AppException


class UnauthorizedException(AppException):
    """
    Raised when authentication is required but not provided or invalid.

    HTTP Status: 401 Unauthorized
    Error Code: UNAUTHORIZED

    Example:
        raise UnauthorizedException(message="Invalid credentials")
    """

    def __init__(
        self, message: str = "Authentication required", details: Optional[dict] = None
    ):
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=401,
            details=details,
        )


class ForbiddenException(AppException):
    """
    Raised when user is authenticated but lacks permission.

    HTTP Status: 403 Forbidden
    Error Code: FORBIDDEN

    Example:
        raise ForbiddenException(message="Insufficient permissions")
    """

    def __init__(
        self, message: str = "Access forbidden", details: Optional[dict] = None
    ):
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=403,
            details=details,
        )


class InvalidTokenException(AppException):
    """
    Raised when authentication token is invalid or expired.

    HTTP Status: 401 Unauthorized
    Error Code: INVALID_TOKEN

    Example:
        raise InvalidTokenException(message="Token has expired")
    """

    def __init__(
        self, message: str = "Invalid or expired token", details: Optional[dict] = None
    ):
        super().__init__(
            code="INVALID_TOKEN",
            message=message,
            status_code=401,
            details=details,
        )
