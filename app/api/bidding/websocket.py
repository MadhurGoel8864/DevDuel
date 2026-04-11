"""
WebSocket bid handler for real-time bidding.

Imports the shared ConnectionManager singleton from connection_manager.py.

Inbound message:
    {"type": "PLACE_BID", "auction_id":"...", "team_id":"...", "user_id":"...", "amount": N}
    {"type": "FINISH_AUCTION", "auction_id":"...", "user_id":"..."}  # organizer only

Outbound broadcast:
    {"type": "SYNC", "server_time":"...", "current_auction": {...}|null}
    {"type": "NEW_HIGHEST_BID", "server_time":"...", "team_id":"...", "team_name":"...", "amount": N}
    {"type": "AUCTION_FINISHED", "server_time":"...", "auction_id":"...", "contest_problem_id":"...", "winning_team_id":"...", "winning_bid": N}
    {"type": "ERROR", "message":"..."}
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect

from app.api.bidding.connection_manager import manager
from app.api.bidding.services.bidding import BiddingService

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


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
    client_host = websocket.client.host if websocket.client else "unknown"
    logger.info(
        f"[WS:CONNECT] client={client_host} | contest={contest_id} | "
        f"room_size_after={len(manager._rooms[contest_id]) + 1}"
    )

    await manager.connect(websocket, contest_id)

    # ── Send SYNC state so reconnecting/late clients can catch up ──────────
    try:
        sync_state = await bidding_service.get_sync_payload(contest_id=contest_id)
        sync_payload = {
            "type": "SYNC",
            "server_time": _now_iso(),
            **sync_state,
        }
        await websocket.send_text(json.dumps(sync_payload))
        logger.info(
            f"[WS:SYNC] Sent state to client={client_host} | contest={contest_id} | "
            f"has_active_auction={sync_payload['current_auction'] is not None}"
        )
    except Exception as exc:
        logger.debug(
            f"[WS:SYNC] Failed to send sync for contest={contest_id}: {exc}"
        )

    try:
        while True:
            # ── Receive raw message ────────────────────────────────────────────
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                raise  # let the outer except handle it

            logger.debug(
                f"[WS:RECV] contest={contest_id} | client={client_host} | raw={raw[:200]}"
            )

            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                logger.warning(
                    f"[WS:INVALID_JSON] contest={contest_id} | client={client_host} | "
                    f"error={e} | raw={raw[:100]!r}"
                )
                await websocket.send_text(
                    json.dumps({"type": "ERROR", "message": "Invalid JSON"})
                )
                continue

            msg_type = data.get("type", "")
            logger.debug(
                f"[WS:MSG_TYPE] contest={contest_id} | type={msg_type!r} | client={client_host}"
            )

            # ── PLACE_BID ─────────────────────────────────────────────────────
            if msg_type == "PLACE_BID":
                team_id = data.get("team_id", "")
                amount = data.get("amount", 0)
                user_id = data.get("user_id", "")
                auction_id = data.get("auction_id", "")

                logger.info(
                    f"[WS:PLACE_BID] contest={contest_id} | auction={auction_id} | "
                    f"team={team_id} | user={user_id} | amount={amount}"
                )

                # Input validation
                if not team_id or not auction_id or not user_id or amount <= 0:
                    logger.warning(
                        f"[WS:PLACE_BID:INVALID_INPUT] contest={contest_id} | "
                        f"team_id={team_id!r} | user_id={user_id!r} | "
                        f"auction_id={auction_id!r} | amount={amount!r}"
                    )
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
                    logger.info(
                        f"[WS:PLACE_BID:SUCCESS] contest={contest_id} | auction={auction_id} | "
                        f"team={team_id} | user={user_id} | new_highest={result['amount']} | "
                        f"broadcasting to room"
                    )
                    await manager.broadcast(
                        contest_id,
                        {
                            "type": "NEW_HIGHEST_BID",
                            "server_time": _now_iso(),
                            "team_id": result["team_id"],
                            "team_name": result.get("team_name"),
                            "amount": result["amount"],
                        },
                    )
                except Exception as exc:
                    error_msg = getattr(exc, "message", str(exc))
                    error_code = getattr(exc, "code", "UNKNOWN")
                    logger.warning(
                        f"[WS:PLACE_BID:REJECTED] contest={contest_id} | auction={auction_id} | "
                        f"team={team_id} | user={user_id} | amount={amount} | "
                        f"code={error_code} | reason={error_msg}"
                    )
                    await websocket.send_text(
                        json.dumps({"type": "ERROR", "message": error_msg})
                    )

            # ── FINISH_AUCTION (manual override — organizer only) ─────────────
            elif msg_type == "FINISH_AUCTION":
                auction_id = data.get("auction_id", "")
                user_id = data.get("user_id", "")

                logger.info(
                    f"[WS:FINISH_AUCTION] Manual trigger | contest={contest_id} | "
                    f"auction={auction_id} | user={user_id} | client={client_host}"
                )

                if not auction_id or not user_id:
                    logger.warning(
                        f"[WS:FINISH_AUCTION:INVALID_INPUT] contest={contest_id} | "
                        f"auction_id={auction_id!r} | user_id={user_id!r}"
                    )
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "ERROR",
                                "message": "FINISH_AUCTION requires auction_id and user_id",
                            }
                        )
                    )
                    continue

                try:
                    # Routes through force_end_auction which verifies organizer auth
                    auction = await bidding_service.force_end_auction(
                        auction_id=auction_id,
                        requesting_user_id=user_id,
                    )
                    # force_end_auction already broadcasts AUCTION_FINISHED
                    logger.info(
                        f"[WS:FINISH_AUCTION:SUCCESS] contest={contest_id} | "
                        f"auction={auction_id} | winner={auction.winning_team_id!r} | "
                        f"winning_bid={auction.winning_bid!r}"
                    )
                except Exception as exc:
                    error_msg = getattr(exc, "message", str(exc))
                    error_code = getattr(exc, "code", "UNKNOWN")
                    logger.error(
                        f"[WS:FINISH_AUCTION:ERROR] contest={contest_id} | "
                        f"auction={auction_id} | user={user_id} | "
                        f"code={error_code} | reason={error_msg}"
                    )
                    await websocket.send_text(
                        json.dumps({"type": "ERROR", "message": error_msg})
                    )

            # ── Unknown message type ───────────────────────────────────────────
            else:
                logger.warning(
                    f"[WS:UNKNOWN_TYPE] contest={contest_id} | client={client_host} | "
                    f"type={msg_type!r}"
                )
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "ERROR",
                            "message": f"Unknown message type: {msg_type}",
                        }
                    )
                )

    except WebSocketDisconnect:
        room_size = len(manager._rooms.get(contest_id, []))
        logger.info(
            f"[WS:DISCONNECT] client={client_host} | contest={contest_id} | "
            f"room_size_after={room_size - 1 if room_size > 0 else 0}"
        )
        manager.disconnect(websocket, contest_id)

    except Exception as exc:
        logger.error(
            f"[WS:CRASH] Unexpected error | contest={contest_id} | "
            f"client={client_host} | error={exc!r}",
            exc_info=True,
        )
        manager.disconnect(websocket, contest_id)
