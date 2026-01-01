"""Base exception class for all application exceptions."""

from typing import Optional


class AppException(Exception):
    """
    Base exception for all application errors.

    This exception should be subclassed for domain-specific errors.
    All AppException instances will be caught by the global exception handler
    and converted to standardized APIResponse format.

    Attributes:
        code: Machine-readable error code (e.g., USER_NOT_FOUND)
        message: Human-readable error message
        status_code: HTTP status code for the response
        details: Optional dictionary with additional error context

    Example:
        raise AppException(
            code="RESOURCE_NOT_FOUND",
            message="The requested resource was not found",
            status_code=404,
            details={"resource_id": "123"}
        )
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: Optional[dict] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"code={self.code!r}, "
            f"message={self.message!r}, "
            f"status_code={self.status_code}, "
            f"details={self.details!r})"
        )
