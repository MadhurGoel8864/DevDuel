from typing import Optional

from app.core.exceptions.base import AppException


class BadRequestException(AppException):
    """
    Raised when the client sends an invalid request.

    HTTP Status: 400 Bad Request
    Error Code: BAD_REQUEST

    Example:
        raise BadRequestException(message="Invalid OAuth state")
    """

    def __init__(
        self,
        message: str = "Bad request",
        details: Optional[dict] = None,
    ):
        super().__init__(
            code="BAD_REQUEST",
            message=message,
            status_code=400,
            details=details,
        )
