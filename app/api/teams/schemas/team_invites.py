"""Team Invite Schemas"""

from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.enums import TeamRole


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Request Schemas ────────────────────────────────────────────────────────────


class InviteMemberData(BaseSchema):
    email: EmailStr
    role: TeamRole
    name: str = ""


class InviteMemberRequest(BaseSchema):
    data: InviteMemberData


class InviteTokenData(BaseSchema):
    token: str


class InviteAcceptRequest(BaseSchema):
    data: InviteTokenData


class InviteDeclineRequest(BaseSchema):
    data: InviteTokenData


# ── Response Schemas ───────────────────────────────────────────────────────────


class InviteResponse(BaseSchema):
    message: str
    is_new_user: bool | None = None


class InviteValidateResponse(BaseSchema):
    """
    Returned when frontend calls GET /teams/invite/validate?token=xxx.
    Frontend uses is_new_user to decide whether to show
    accept/decline page or register page.
    """

    team_id: str
    team_name: str | None
    email: str
    role: str
    is_new_user: bool
