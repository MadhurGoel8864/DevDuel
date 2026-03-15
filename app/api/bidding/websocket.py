"""
WebSocket bid handler for real-time bidding.

Imports the shared ConnectionManager singleton from connection_manager.py.

Inbound message:
    {"type": "PLACE_BID", "auction_id":"...", "team_id":"...", "user_id":"...", "amount": N}
    {"type": "FINISH_AUCTION", "auction_id":"..."}  # manual override

Outbound broadcast:
    {"type": "NEW_HIGHEST_BID", "team_id":"...", "amount": N}
    {"type": "ERROR", "message":"..."}
    {"type": "AUCTION_FINISHED", "auction_id":"...", "winning_team_id":"...", "winning_bid": N}
"""

import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from app.api.bidding.connection_manager import manager
from app.api.bidding.services.bidding import BiddingService

logger = logging.getLogger(__name__)


async def bidding_ws_endpoint(
    websocket: WebSocket,
    contest_id: str,
    bidding_service: BiddingService,
) -> None:
    """
    WebSocket handler for real-time bidding in a contest.

    Connection lifecycle:
      1. Client connects  →  accepted into the contest room.
      2. Client sends PLACE_BID / FINISH_AUCTION message.
      3. Service validates and processes.
      4. On success, broadcast result to everyone in the room.
      5. On error, send ERROR message back to the sender only.
      6. Client disconnects  →  removed from the room.
    """
    await manager.connect(websocket, contest_id)
    try:
        while True:
            try:
                raw = await websocket.receive_text()
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "ERROR", "message": "Invalid JSON"})
                )
                continue

            msg_type = data.get("type", "")

            # ── PLACE_BID ─────────────────────────────────────────────────────
            if msg_type == "PLACE_BID":
                team_id = data.get("team_id", "")
                amount = data.get("amount", 0)
                user_id = data.get("user_id", "")
                auction_id = data.get("auction_id", "")

                if not team_id or not auction_id or not user_id or amount <= 0:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "ERROR",
                                "message": "PLACE_BID requires team_id, user_id, auction_id, and a positive amount.",
                            }
                        )
                    )
                    continue

                try:
                    result = await bidding_service.place_bid(
                        auction_id=auction_id,
                        team_id=team_id,
                        user_id=user_id,
                        amount=amount,
                    )
                    await manager.broadcast(
                        contest_id,
                        {
                            "type": "NEW_HIGHEST_BID",
                            "team_id": result["team_id"],
                            "amount": result["amount"],
                        },
                    )
                except Exception as exc:
                    error_msg = getattr(exc, "message", str(exc))
                    await websocket.send_text(
                        json.dumps({"type": "ERROR", "message": error_msg})
                    )

            # ── FINISH_AUCTION (manual override) ──────────────────────────────
            elif msg_type == "FINISH_AUCTION":
                auction_id = data.get("auction_id", "")
                if not auction_id:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "ERROR",
                                "message": "FINISH_AUCTION requires auction_id",
                            }
                        )
                    )
                    continue
                try:
                    assignment = await bidding_service.finish_auction(
                        auction_id=auction_id
                    )
                    await manager.broadcast(
                        contest_id,
                        {
                            "type": "AUCTION_FINISHED",
                            "auction_id": auction_id,
                            "winning_team_id": (
                                assignment.team_id if assignment else None
                            ),
                            "winning_bid": (
                                assignment.winning_bid if assignment else None
                            ),
                        },
                    )
                except Exception as exc:
                    error_msg = getattr(exc, "message", str(exc))
                    await websocket.send_text(
                        json.dumps({"type": "ERROR", "message": error_msg})
                    )

            else:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "ERROR",
                            "message": f"Unknown message type: {msg_type}",
                        }
                    )
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket, contest_id)
    except Exception as exc:
        logger.error(f"Unexpected WS error in contest {contest_id}: {exc}")
        manager.disconnect(websocket, contest_id)
