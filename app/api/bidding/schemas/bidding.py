"""Bidding API Pydantic Schemas"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.core.enums import AssignmentStatus, AuctionStatus
from app.core.responses import APIResponse


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Request Schemas ────────────────────────────────────────────────────────────


class StartAuctionData(BaseSchema):
    """Data payload for starting an auction."""

    contest_problem_id: str
    duration_seconds: int = 60


class StartAuctionRequest(BaseSchema):
    data: StartAuctionData


# ── WebSocket Message Schemas ──────────────────────────────────────────────────


class BidMessage(BaseSchema):
    """Inbound WebSocket message from a client placing a bid."""

    type: str  # must equal "PLACE_BID"
    team_id: str
    amount: int


class BidBroadcast(BaseSchema):
    """Outbound WebSocket message broadcast to all contest clients."""

    type: str = "NEW_HIGHEST_BID"
    team_id: str
    amount: int


# ── Response Schemas ───────────────────────────────────────────────────────────


class AuctionResponseData(BaseSchema):
    """Full auction details returned by the HTTP layer."""

    id: str
    contest_id: str
    contest_problem_id: str
    status: AuctionStatus
    base_price: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    winning_team_id: Optional[str] = None
    winning_bid: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class AuctionResultData(BaseSchema):
    """Result payload returned after an auction finishes."""

    auction_id: str
    contest_problem_id: str
    winning_team_id: Optional[str] = None
    winning_bid: Optional[int] = None
    status: AuctionStatus


class AssignmentResponseData(BaseSchema):
    """Tracks a team's won problem assignment."""

    id: str
    contest_id: str
    contest_problem_id: str
    team_id: str
    winning_bid: int
    status: AssignmentStatus
    created_at: datetime


# ── Response Aliases ───────────────────────────────────────────────────────────

AuctionResponse = APIResponse[AuctionResponseData]
AuctionListResponse = APIResponse[List[AuctionResponseData]]
AuctionResultResponse = APIResponse[AuctionResultData]
