"""Team domain exceptions."""

from typing import Optional

from app.core.exceptions.base import AppException


class TeamNotFoundException(AppException):
    """Raised when a team is not found. HTTP 404."""

    def __init__(self, team_id: Optional[str] = None, message: Optional[str] = None):
        details = {"team_id": team_id} if team_id else None
        super().__init__(
            code="TEAM_NOT_FOUND",
            message=message
            or (f"Team with ID '{team_id}' not found" if team_id else "Team not found"),
            status_code=404,
            details=details,
        )


class TeamAlreadyExistsException(AppException):
    """Raised when a team with the same name already exists. HTTP 409."""

    def __init__(self, name: Optional[str] = None, message: Optional[str] = None):
        details = {"name": name} if name else None
        super().__init__(
            code="TEAM_ALREADY_EXISTS",
            message=message
            or (
                f"Team with name '{name}' already exists"
                if name
                else "Team already exists"
            ),
            status_code=409,
            details=details,
        )


class TeamMemberNotFoundException(AppException):
    """Raised when a team member is not found. HTTP 404."""

    def __init__(self, user_id: Optional[str] = None, team_id: Optional[str] = None):
        details = {"user_id": user_id, "team_id": team_id}
        super().__init__(
            code="TEAM_MEMBER_NOT_FOUND",
            message="Team member not found",
            status_code=404,
            details=details,
        )


class TeamMemberAlreadyExistsException(AppException):
    """Raised when a user is already a member of the team. HTTP 409."""

    def __init__(self, user_id: Optional[str] = None, team_id: Optional[str] = None):
        details = {"user_id": user_id, "team_id": team_id}
        super().__init__(
            code="TEAM_MEMBER_ALREADY_EXISTS",
            message="User is already a member of this team",
            status_code=409,
            details=details,
        )


class TeamRoleTakenException(AppException):
    """Raised when the requested team role is already occupied. HTTP 400."""

    def __init__(self, role: Optional[str] = None):
        details = {"role": role} if role else None
        super().__init__(
            code="TEAM_ROLE_TAKEN",
            message=(
                f"The '{role}' role is already taken in this team"
                if role
                else "This team role is already taken"
            ),
            status_code=400,
            details=details,
        )


class NotTeamCreatorException(AppException):
    """Raised when a non-creator tries a creator-only action. HTTP 403."""

    def __init__(self, message: Optional[str] = None):
        super().__init__(
            code="NOT_TEAM_CREATOR",
            message=message or "Only the team creator can perform this action",
            status_code=403,
        )


class TeamMemberSameRoleException(AppException):
    """Raised when both members already share the same role — nothing to swap. HTTP 400."""

    def __init__(self, role: Optional[str] = None):
        details = {"role": role} if role else None
        super().__init__(
            code="TEAM_MEMBER_SAME_ROLE",
            message=(
                f"Both members are already in the '{role}' group — no swap needed"
                if role
                else "Both members already have the same role"
            ),
            status_code=400,
            details=details,
        )
class CannotModifyTeamDuringActiveContest(AppException):
    """Raised when a team roster/deletion is attempted while the team is in an ACTIVE contest. HTTP 409."""

    def __init__(self, team_id: Optional[str] = None, contest_id: Optional[str] = None):
        details: Optional[dict] = None
        if team_id or contest_id:
            details = {}
            if team_id:
                details["team_id"] = team_id
            if contest_id:
                details["contest_id"] = contest_id
        super().__init__(
            code="CANNOT_MODIFY_TEAM_DURING_ACTIVE_CONTEST",
            message="Team cannot be modified while participating in an active contest",
            status_code=409,
            details=details,
        )
