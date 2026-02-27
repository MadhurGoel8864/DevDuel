"""Exception module exports."""

from app.core.exceptions.auth import (
    ForbiddenException,
    InvalidTokenException,
    UnauthorizedException,
)
from app.core.exceptions.base import AppException
from app.core.exceptions.common import BadRequestException
from app.core.exceptions.contests import (
    ContestAlreadyRegisteredException,
    ContestNotActiveException,
    ContestNotFoundException,
)
from app.core.exceptions.teams import (
    NotTeamCreatorException,
    TeamAlreadyExistsException,
    TeamMemberAlreadyExistsException,
    TeamMemberNotFoundException,
    TeamNotFoundException,
    TeamRoleTakenException,
)
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
    # Team exceptions
    "TeamNotFoundException",
    "TeamAlreadyExistsException",
    "TeamMemberNotFoundException",
    "TeamMemberAlreadyExistsException",
    "TeamRoleTakenException",
    "NotTeamCreatorException",
    # Contest exceptions
    "ContestNotFoundException",
    "ContestAlreadyRegisteredException",
    "ContestNotActiveException",
]
