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


# ── Invite Exceptions ──────────────────────────────────────────────────────────


class TeamInviteInvalidException(AppException):
    """Token not found in Redis — expired or never existed. HTTP 404."""

    def __init__(self):
        super().__init__(
            code="INVITE_INVALID",
            message="Invite token is invalid or has expired. Please ask for a new invite.",
            status_code=404,
        )


class TeamInviteEmailMismatchException(AppException):
    """Authenticated user's email doesn't match the invite email. HTTP 403."""

    def __init__(self):
        super().__init__(
            code="INVITE_EMAIL_MISMATCH",
            message="This invite was sent to a different email address.",
            status_code=403,
        )


class TeamInviteAlreadyPendingException(AppException):
    """A pending invite already exists for this email+team combo. HTTP 409."""

    def __init__(self, email: Optional[str] = None):
        super().__init__(
            code="INVITE_ALREADY_PENDING",
            message=(
                f"A pending invite already exists for {email}"
                if email
                else "A pending invite already exists for this email"
            ),
            status_code=409,
            details={"email": email} if email else None,
        )


"""Team exceptions — add CannotLeaveOwnTeamException"""


class CannotLeaveOwnTeamException(AppException):
    """Raised when the team creator tries to use the leave endpoint."""

    def __init__(self, team_id: str):
        super().__init__(
            status_code=403,
            code="CANNOT_LEAVE_OWN_TEAM",
            message=(
                "Team creators cannot leave their own team. " "Delete the team instead."
            ),
            details={"team_id": team_id},
        )


class TeamNotReadyForSwapException(AppException):
    """
    Raised when swap-roles is called but team doesn't have exactly 2 members.
    HTTP 400.
    """

    def __init__(self, team_id: str, member_count: int):
        super().__init__(
            code="TEAM_NOT_READY_FOR_SWAP",
            message=(
                f"Team must have exactly 2 members to swap roles, "
                f"but has {member_count}."
            ),
            status_code=400,
            details={"team_id": team_id, "member_count": member_count},
        )


# NOTE: TeamInviteExpiredException and TeamInviteConsumedException from the DB
# approach are no longer needed — Redis returns None for both expired and
# consumed tokens, and TeamInviteInvalidException covers both cases.


# ── Join Request Exceptions ────────────────────────────────────────────────────


class JoinRequestAlreadyPendingException(AppException):
    """Raised when a user already has a PENDING join request. HTTP 409."""

    def __init__(self, team_id: Optional[str] = None):
        super().__init__(
            code="JOIN_REQUEST_ALREADY_PENDING",
            message=(
                "You already have a pending join request. "
                "Cancel it before sending a new one."
            ),
            status_code=409,
            details={"team_id": team_id} if team_id else None,
        )


class JoinRequestNotFoundException(AppException):
    """Raised when a join request is not found. HTTP 404."""

    def __init__(self, request_id: Optional[str] = None):
        super().__init__(
            code="JOIN_REQUEST_NOT_FOUND",
            message=(
                f"Join request '{request_id}' not found"
                if request_id
                else "Join request not found"
            ),
            status_code=404,
            details={"request_id": request_id} if request_id else None,
        )


class JoinRequestAlreadyResolvedException(AppException):
    """Raised when accept/reject/cancel is called on a non-PENDING request. HTTP 409."""

    def __init__(self, status: Optional[str] = None):
        super().__init__(
            code="JOIN_REQUEST_ALREADY_RESOLVED",
            message=(
                f"Join request is already {status.lower()}"
                if status
                else "Join request is already resolved"
            ),
            status_code=409,
            details={"status": status} if status else None,
        )


class TeamHasNoOpenSlotsException(AppException):
    """Raised when attempting to request a team that has no open role slots. HTTP 409."""

    def __init__(self, team_id: Optional[str] = None):
        super().__init__(
            code="TEAM_HAS_NO_OPEN_SLOTS",
            message="This team has no open role slots.",
            status_code=409,
            details={"team_id": team_id} if team_id else None,
        )


class CannotRequestOwnTeamException(AppException):
    """Raised when a team creator tries to send a join request to their own team. HTTP 400."""

    def __init__(self, team_id: Optional[str] = None):
        super().__init__(
            code="CANNOT_REQUEST_OWN_TEAM",
            message="You cannot send a join request to your own team.",
            status_code=400,
            details={"team_id": team_id} if team_id else None,
        )


class JoinRequestPermissionDeniedException(AppException):
    """Raised when a user tries to act on a join request they don't own/manage. HTTP 403."""

    def __init__(self, message: Optional[str] = None):
        super().__init__(
            code="JOIN_REQUEST_PERMISSION_DENIED",
            message=message or "You are not allowed to act on this join request.",
            status_code=403,
        )
