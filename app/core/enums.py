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


class JoinRequestStatus(str, Enum):
    """Lifecycle status for a TeamJoinRequest."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


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


class ProblemKind(str, Enum):
    """Discriminator for ContestProblem: which problem table it references."""

    BUILTIN = "builtin"
    CUSTOM = "custom"


class AuctionStatus(str, Enum):
    """Lifecycle status for a ProblemAuction."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    FINISHED = "FINISHED"


class AssignmentStatus(str, Enum):
    """Status of a ContestProblemAssignment."""

    ASSIGNED = "ASSIGNED"
    SOLVED = "SOLVED"
    FAILED = "FAILED"


class SubmissionVerdict(str, Enum):
    """Overall verdict for a code submission."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    WRONG_ANSWER = "WRONG_ANSWER"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ValidationStatus(str, Enum):
    """Validation status for a custom problem's test cases."""

    UNVALIDATED = "UNVALIDATED"
    VALID = "VALID"
    INVALID = "INVALID"
