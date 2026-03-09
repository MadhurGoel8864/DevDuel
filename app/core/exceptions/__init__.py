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
    ContestNotFoundException,
    InvalidContestStateTransition,
    RegistrationClosedException,
)
from app.core.exceptions.problems import (
    InvalidProblemOrderException,
    ProblemAlreadyInContestException,
    ProblemNotFoundException,
)
from app.core.exceptions.teams import (
    CannotModifyTeamDuringActiveContest,
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
    "CannotModifyTeamDuringActiveContest",
    # Contest exceptions
    "ContestNotFoundException",
    "ContestAlreadyRegisteredException",
    "RegistrationClosedException",
    "InvalidContestStateTransition",
    "BadRequestException",
    # Problem exceptions
    "ProblemNotFoundException",
    "ProblemAlreadyInContestException",
    "InvalidProblemOrderException",
]
