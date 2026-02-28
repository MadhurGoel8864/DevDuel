"""Contests API Schemas"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.core.responses import APIResponse
from app.core.timezone_utils import ISTDatetimeMixin


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Request Schemas ────────────────────────────────────────────────────────────


class ContestCreateData(BaseSchema):
    name: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime


class ContestCreateRequest(BaseSchema):
    data: ContestCreateData


class RegisterTeamData(BaseSchema):
    team_id: str


class RegisterTeamRequest(BaseSchema):
    data: RegisterTeamData


# ── Response Schemas ───────────────────────────────────────────────────────────


class TeamContestResponseData(BaseSchema, ISTDatetimeMixin):
    id: str
    team_id: str
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
    is_active: bool
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
    is_active: bool
    created_at: datetime


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
    score: int
    currency: int


# ── Final Response Aliases ─────────────────────────────────────────────────────

ContestResponse = APIResponse[ContestResponseData]
ContestListResponse = APIResponse[list[ContestSummaryData]]
TeamContestDetailResponse = APIResponse[TeamContestDetailData]
LeaderboardResponse = APIResponse[list[LeaderboardEntryData]]
