"""Bidding API Routes"""

import logging

from fastapi import APIRouter, Depends, WebSocket

from app.api.users.dao.users import UserDAO, get_user_dao
from app.api.bidding.handlers.bidding import (
    force_end_auction_handler,
    get_all_auctions_handler,
    get_auction_result_handler,
    get_current_auction_handler,
    start_auction_handler,
    tab_switch_handler,
)
from app.api.bidding.services.bidding import BiddingService, get_bidding_service
from app.api.bidding.websocket import bidding_ws_endpoint
from app.core.enums import TokenType
from app.core.security import decode_token

logger = logging.getLogger(__name__)

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
    "/contests/{contest_id}/auctions",
    get_all_auctions_handler,
    methods=["GET"],
    summary="List All Auctions",
    description="Return all auctions for a contest, ordered by created_at ascending.",
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

router.add_api_route(
    "/auctions/{auction_id}/end",
    force_end_auction_handler,
    methods=["POST"],
    summary="Force End Auction",
    description="Immediately end an active auction. Organizer of the contest only.",
)

router.add_api_route(
    "/contests/{contest_id}/tab-switch",
    tab_switch_handler,
    methods=["POST"],
    status_code=200,
    summary="Record Tab Switch",
    description="Record a tab visibility change for a contest participant. Notifies organizers via WebSocket.",
)

# ── WebSocket Endpoint ─────────────────────────────────────────────────────────


@router.websocket("/ws/{contest_id}")
async def ws_bidding(
    websocket: WebSocket,
    contest_id: str,
    bidding_service: BiddingService = Depends(get_bidding_service),
    user_dao: UserDAO = Depends(get_user_dao),
):
    """
    WebSocket endpoint for real-time bidding.

    Connect to receive bid updates and place bids:
      ws://<host>/api/bidding/ws/{contest_id}?token=<jwt_access_token>

    Authentication:
      The client MUST pass a valid JWT access token as the `token` query
      parameter. The server-side bid handler uses this identity instead of
      whatever `user_id` the client puts in the payload — otherwise any
      browser tab could bid as any user.

    Inbound:  {"type": "PLACE_BID", "team_id": "...", "auction_id": "...", "amount": N}
              {"type": "FINISH_AUCTION", "auction_id": "..."}  # organizer only
    Outbound: {"type": "NEW_HIGHEST_BID", "team_id": "...", "amount": N}
    """
    token = websocket.query_params.get("token")
    if not token:
        logger.warning(
            f"[WS:AUTH] rejected — no token | contest={contest_id}"
        )
        await websocket.close(code=4401, reason="Missing auth token")
        return

    try:
        payload = decode_token(token)
        if payload.get("type") != TokenType.ACCESS.value:
            raise ValueError("not an access token")
        authenticated_user_id = payload.get("sub")
        if not authenticated_user_id:
            raise ValueError("missing sub claim")
        user = await user_dao.get_by_id(authenticated_user_id)
        if not user or not user.is_active or not user.is_verified:
            raise ValueError("user not active/verified")
    except Exception as exc:
        logger.warning(
            f"[WS:AUTH] rejected — invalid token | contest={contest_id} | "
            f"error={exc!r}"
        )
        await websocket.close(code=4401, reason="Invalid auth token")
        return

    await bidding_ws_endpoint(
        websocket=websocket,
        contest_id=contest_id,
        bidding_service=bidding_service,
        authenticated_user_id=authenticated_user_id,
    )
