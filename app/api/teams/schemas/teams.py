"""Teams API Schemas"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import TeamRole
from app.core.responses import APIResponse
from app.core.timezone_utils import ISTDatetimeMixin


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Request Schemas ────────────────────────────────────────────────────────────


class TeamCreateData(BaseSchema):
    name: str


class TeamCreateRequest(BaseSchema):
    data: TeamCreateData


class AddMemberData(BaseSchema):
    user_id: str
    role: TeamRole


class AddMemberRequest(BaseSchema):
    data: AddMemberData


class SwapRolesData(BaseSchema):
    member1_id: str  
    member2_id: str  # TeamMember.id (not User.id)


class SwapRolesRequest(BaseSchema):
    data: SwapRolesData


# ── Response Schemas ───────────────────────────────────────────────────────────


class TeamMemberResponseData(BaseSchema, ISTDatetimeMixin):
    id: str
    team_id: str
    user_id: str
    role: TeamRole
    created_at: datetime


class TeamResponseData(BaseSchema, ISTDatetimeMixin):
    id: str
    name: str
    created_by: str
    members: list[TeamMemberResponseData] = []
    created_at: datetime
    updated_at: datetime


class TeamSummaryData(BaseSchema, ISTDatetimeMixin):
    """Lightweight team data for list endpoints."""

    id: str
    name: str
    created_by: str
    created_at: datetime


# ── Final Response Aliases ─────────────────────────────────────────────────────

TeamResponse = APIResponse[TeamResponseData]
TeamListResponse = APIResponse[list[TeamSummaryData]]