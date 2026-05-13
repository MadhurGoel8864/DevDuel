from app.core.exceptions.base import AppException


class RateLimitExceededException(AppException):
    def __init__(self, retry_after: int):
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=f"Too many requests. Try again in {retry_after} seconds.",
            status_code=429,
            details={"retry_after_seconds": retry_after},
        )
