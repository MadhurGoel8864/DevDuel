"""Contests API Schemas"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import ContestStatus
from app.core.responses import APIResponse, PaginatedResponse
from app.core.timezone_utils import ISTDatetimeMixin


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Request Schemas ────────────────────────────────────────────────────────────


class ContestCreateData(BaseSchema):
    name: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    starting_currency: int = Field(default=1000, ge=1, le=10_000)
    allowed_email_domain: Optional[str] = None


class ContestCreateRequest(BaseSchema):
    data: ContestCreateData


class RegisterTeamData(BaseSchema):
    team_id: str


class RegisterTeamRequest(BaseSchema):
    data: RegisterTeamData


class ContestEditData(BaseSchema):
    """All fields optional — only provided fields are updated (partial update)."""

    name: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    starting_currency: Optional[int] = Field(default=None, ge=1, le=10_000)
    allowed_email_domain: Optional[str] = None


class ContestEditRequest(BaseSchema):
    data: ContestEditData


# ── Response Schemas ───────────────────────────────────────────────────────────


class TeamContestResponseData(BaseSchema, ISTDatetimeMixin):
    id: str
    team_id: str
    team_name: str = ""
    contest_id: str
    currency: int
    score: int
    created_at: datetime


class ContestResponseData(BaseSchema, ISTDatetimeMixin):
    id: str
    name: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    status: ContestStatus
    created_by: str
    starting_currency: int
    allowed_email_domain: Optional[str] = None
    teams: list[TeamContestResponseData] = []
    created_at: datetime
    updated_at: datetime


class ContestSummaryData(BaseSchema, ISTDatetimeMixin):
    """Lightweight contest data for list endpoints."""

    id: str
    name: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    status: ContestStatus
    created_by: str
    starting_currency: int
    allowed_email_domain: Optional[str] = None
    created_at: datetime
    team_count: int = 0

    @model_validator(mode="before")
    @classmethod
    def compute_team_count(cls, data):
        if hasattr(data, "teams"):
            return {
                "id": data.id,
                "name": data.name,
                "description": data.description,
                "start_time": data.start_time,
                "end_time": data.end_time,
                "status": data.status,
                "created_by": data.created_by,
                "starting_currency": data.starting_currency,
                "allowed_email_domain": data.allowed_email_domain,
                "created_at": data.created_at,
                "team_count": len(data.teams),
            }
        return data


# ── Registered Teams Schema ───────────────────────────────────────────────────


class RegisteredTeamData(BaseSchema):
    """Brief team info for the registered-teams list endpoint."""

    team_id: str
    team_name: str


# ── Leaderboard / Team-in-Contest Schemas ────────────────────────────────────


class TeamContestDetailData(BaseSchema, ISTDatetimeMixin):
    """Full TeamContest state for a single team — used by the dashboard endpoint."""

    id: str
    team_id: str
    contest_id: str
    currency: int
    score: int
    created_at: datetime


class LeaderboardEntryData(BaseSchema):
    """One row on the leaderboard — ordered by score desc, then currency desc."""

    rank: int
    team_id: str
    team_name: str = ""
    score: int
    currency: int


class DetailedLeaderboardEntryData(BaseSchema):
    """Enriched leaderboard row for the organizer post-contest view."""

    rank: int
    team_id: str
    team_name: str = ""
    score: int
    currency: int
    problems_won: int = 0
    problems_solved: int = 0
    total_currency_spent: int = 0
    avg_bid: float = 0.0
    points_per_credit: float = 0.0
    has_any_submission: bool = False
    attempted_problem_ids: list[str] = []
    solved_problem_ids: list[str] = []


# ── User Registration Check ───────────────────────────────────────────────────


class UserRegistrationCheckData(BaseSchema):
    """Whether a user is registered in a contest."""

    contest_id: str
    user_id: str
    is_registered: bool


# ── Final Response Aliases ─────────────────────────────────────────────────────

ContestRegisteredTeamsResponse = APIResponse[list[RegisteredTeamData]]
ContestResponse = APIResponse[ContestResponseData]
ContestListResponse = APIResponse[list[ContestSummaryData]]
ContestPaginatedListResponse = PaginatedResponse[ContestSummaryData]
TeamContestDetailResponse = APIResponse[TeamContestDetailData]
LeaderboardResponse = APIResponse[list[LeaderboardEntryData]]
DetailedLeaderboardResponse = APIResponse[list[DetailedLeaderboardEntryData]]
UserRegistrationCheckResponse = APIResponse[UserRegistrationCheckData]
