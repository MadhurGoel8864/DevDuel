from enum import Enum


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class UserRole(str, Enum):
    """User role enumeration."""

    USER = "user"
    ADMIN = "admin"


class PlatformType(str, Enum):
    """Platform type enumeration."""

    WEB = "web"
    APP = "app"
