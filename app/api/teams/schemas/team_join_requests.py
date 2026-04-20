"""Team Join Request Schemas"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import JoinRequestStatus, TeamRole
from app.core.responses import APIResponse, PaginatedResponse
from app.core.timezone_utils import ISTDatetimeMixin


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Request Schemas ────────────────────────────────────────────────────────────


class JoinRequestCreateData(BaseSchema):
    team_id: str


class JoinRequestCreateRequest(BaseSchema):
    data: JoinRequestCreateData


# ── Response Schemas ───────────────────────────────────────────────────────────


class JoinRequestResponseData(BaseSchema, ISTDatetimeMixin):
    id: str
    team_id: str
    team_name: str | None = None
    user_id: str
    requester_username: str | None = None
    requester_email: str | None = None
    role: TeamRole
    status: JoinRequestStatus
    created_at: datetime
    updated_at: datetime


class BrowseTeamItemData(BaseSchema, ISTDatetimeMixin):
    id: str
    name: str
    creator_username: str | None = None
    member_count: int
    is_open: bool
    open_roles: list[TeamRole]
    created_at: datetime


# ── Final Response Aliases ─────────────────────────────────────────────────────

JoinRequestResponse = APIResponse[JoinRequestResponseData]
JoinRequestListResponse = APIResponse[list[JoinRequestResponseData]]
BrowseTeamsResponse = PaginatedResponse[BrowseTeamItemData]
