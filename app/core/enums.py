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


class TeamRole(str, Enum):
    BIDDING = "BIDDING"
    CODING = "CODING"


class ContestStatus(str, Enum):
    """Lifecycle status for a Contest."""

    DRAFT = "DRAFT"
    REGISTRATION_OPEN = "REGISTRATION_OPEN"
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"


class Difficulty(str, Enum):
    """Difficulty level for a coding Problem."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
