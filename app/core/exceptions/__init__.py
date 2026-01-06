"""Exception module exports."""

from app.core.exceptions.auth import (
    ForbiddenException,
    InvalidTokenException,
    UnauthorizedException,
)
from app.core.exceptions.base import AppException
from app.core.exceptions.users import (
    UserAlreadyExistsException,
    UserNotFoundException,
    UserValidationException,
)

__all__ = [
    # Base
    "AppException",
    # User exceptions
    "UserNotFoundException",
    "UserAlreadyExistsException",
    "UserValidationException",
    # Auth exceptions
    "UnauthorizedException",
    "ForbiddenException",
    "InvalidTokenException",
]
