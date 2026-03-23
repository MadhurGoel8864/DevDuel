"""Teams API Schemas"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.core.enums import TeamRole
from app.core.responses import APIResponse, PaginatedResponse
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


# SwapRolesRequest removed — team has exactly 2 members,
# service auto-fetches both and swaps without needing input.


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
    member_count: int = 0

    @model_validator(mode="before")
    @classmethod
    def compute_member_count(cls, data):
        if hasattr(data, "members"):
            return {
                "id": data.id,
                "name": data.name,
                "created_by": data.created_by,
                "created_at": data.created_at,
                "member_count": len(data.members),
            }
        return data


# ── Status / Role / Can-Join Schemas ──────────────────────────────────────────


class TeamStatusResponseData(BaseSchema):
    is_ready: bool
    has_bidder: bool
    has_coder: bool
    member_count: int
    missing_roles: list[str]


class TeamRoleResponseData(BaseSchema):
    team_id: str
    user_id: str
    role: TeamRole | None
    is_member: bool


class CanJoinResponseData(BaseSchema):
    team_id: str
    contest_id: str
    can_join: bool
    reasons: list[str]


# ── Final Response Aliases ─────────────────────────────────────────────────────

TeamResponse = APIResponse[TeamResponseData]
TeamListResponse = APIResponse[list[TeamSummaryData]]
TeamPaginatedListResponse = PaginatedResponse[TeamSummaryData]
TeamStatusResponse = APIResponse[TeamStatusResponseData]
TeamRoleResponse = APIResponse[TeamRoleResponseData]
CanJoinResponse = APIResponse[CanJoinResponseData]
