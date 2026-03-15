"""Bidding API Routes"""

from fastapi import APIRouter, Depends, WebSocket

from app.api.bidding.handlers.bidding import (
    get_auction_result_handler,
    get_current_auction_handler,
    start_auction_handler,
)
from app.api.bidding.services.bidding import BiddingService, get_bidding_service
from app.api.bidding.websocket import bidding_ws_endpoint

router = APIRouter(prefix="/bidding", tags=["Bidding"])

# ── HTTP Endpoints ─────────────────────────────────────────────────────────────

router.add_api_route(
    "/contests/{contest_id}/auctions/start",
    start_auction_handler,
    methods=["POST"],
    status_code=201,
    summary="Start Auction",
    description="Start an auction for the next problem in an ACTIVE contest.",
)

router.add_api_route(
    "/contests/{contest_id}/auctions/current",
    get_current_auction_handler,
    methods=["GET"],
    summary="Get Current Auction",
    description="Return the currently active (or most recent) auction for a contest.",
)

router.add_api_route(
    "/auctions/{auction_id}/result",
    get_auction_result_handler,
    methods=["GET"],
    summary="Get Auction Result",
    description="Return the final result of a finished auction.",
)

# ── WebSocket Endpoint ─────────────────────────────────────────────────────────


@router.websocket("/ws/{contest_id}")
async def ws_bidding(
    websocket: WebSocket,
    contest_id: str,
    bidding_service: BiddingService = Depends(get_bidding_service),
):
    """
    WebSocket endpoint for real-time bidding.

    Connect to receive bid updates and place bids:
      ws://<host>/api/bidding/ws/{contest_id}

    Inbound:  {"type": "PLACE_BID", "team_id": "...", "user_id": "...", "auction_id": "...", "amount": N}
    Outbound: {"type": "NEW_HIGHEST_BID", "team_id": "...", "amount": N}
    """
    await bidding_ws_endpoint(
        websocket=websocket,
        contest_id=contest_id,
        bidding_service=bidding_service,
    )
