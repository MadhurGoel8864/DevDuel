"""
WebSocket bid handler for real-time bidding.

Imports the shared ConnectionManager singleton from connection_manager.py.

Inbound message:
    {"type": "PLACE_BID", "auction_id": "...", "team_id": "...", "amount": N}
    {"type": "FINISH_AUCTION", "auction_id": "..."}  # organizer only

Note: `user_id` in the payload is IGNORED. The caller is identified by the
JWT `token` query parameter validated in `routes/bidding.py` before this
handler runs — passing the user_id through the wire would let anyone bid
as anyone.

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
    authenticated_user_id: str,
) -> None:
    """
    WebSocket handler for real-time bidding in a contest.

    `authenticated_user_id` is the `sub` claim of the JWT passed as the
    `?token=` query param when the socket was opened. It is the only
    identity the server will trust — any `user_id` field in inbound
    messages is ignored.
    """
    client_host = websocket.client.host if websocket.client else "unknown"

    await manager.connect(websocket, contest_id)
    logger.info(
        f"[WS:CONNECT] client={client_host} | contest={contest_id} | "
        f"user={authenticated_user_id} | room_size={manager.room_size(contest_id)}"
    )

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

            if not isinstance(data, dict):
                await websocket.send_text(
                    json.dumps(
                        {"type": "ERROR", "message": "Message must be a JSON object"}
                    )
                )
                continue

            msg_type = data.get("type", "")
            logger.debug(
                f"[WS:MSG_TYPE] contest={contest_id} | type={msg_type!r} | client={client_host}"
            )

            # ── PLACE_BID ─────────────────────────────────────────────────────
            if msg_type == "PLACE_BID":
                team_id = data.get("team_id")
                amount = data.get("amount")
                auction_id = data.get("auction_id")

                logger.info(
                    f"[WS:PLACE_BID] contest={contest_id} | auction={auction_id} | "
                    f"team={team_id} | user={authenticated_user_id} | amount={amount}"
                )

                # Strict input validation — JSON-decoded values can be any type,
                # and the downstream service assumes ints for currency math.
                if (
                    not isinstance(team_id, str)
                    or not team_id
                    or not isinstance(auction_id, str)
                    or not auction_id
                ):
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "ERROR",
                                "message": "PLACE_BID requires non-empty string team_id and auction_id",
                            }
                        )
                    )
                    continue
                # `True`/`False` are ints in Python; exclude them explicitly.
                if (
                    not isinstance(amount, int)
                    or isinstance(amount, bool)
                    or amount <= 0
                ):
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "ERROR",
                                "message": "PLACE_BID amount must be a positive integer",
                            }
                        )
                    )
                    continue

                try:
                    result = await bidding_service.place_bid(
                        auction_id=auction_id,
                        team_id=team_id,
                        user_id=authenticated_user_id,
                        amount=amount,
                    )
                    logger.info(
                        f"[WS:PLACE_BID:SUCCESS] contest={contest_id} | auction={auction_id} | "
                        f"team={team_id} | user={authenticated_user_id} | "
                        f"new_highest={result['amount']} | broadcasting to room"
                    )
                    await manager.broadcast(
                        contest_id,
                        {
                            "type": "NEW_HIGHEST_BID",
                            "server_time": _now_iso(),
                            "auction_id": auction_id,
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
                        f"team={team_id} | user={authenticated_user_id} | amount={amount} | "
                        f"code={error_code} | reason={error_msg}"
                    )
                    await websocket.send_text(
                        json.dumps({"type": "ERROR", "message": error_msg})
                    )

            # ── FINISH_AUCTION (manual override — organizer only) ─────────────
            elif msg_type == "FINISH_AUCTION":
                auction_id = data.get("auction_id")

                logger.info(
                    f"[WS:FINISH_AUCTION] Manual trigger | contest={contest_id} | "
                    f"auction={auction_id} | user={authenticated_user_id} | client={client_host}"
                )

                if not isinstance(auction_id, str) or not auction_id:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "ERROR",
                                "message": "FINISH_AUCTION requires a non-empty string auction_id",
                            }
                        )
                    )
                    continue

                try:
                    # Routes through force_end_auction which verifies organizer auth
                    auction = await bidding_service.force_end_auction(
                        auction_id=auction_id,
                        requesting_user_id=authenticated_user_id,
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
                        f"auction={auction_id} | user={authenticated_user_id} | "
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
        manager.disconnect(websocket, contest_id)
        logger.info(
            f"[WS:DISCONNECT] client={client_host} | contest={contest_id} | "
            f"room_size={manager.room_size(contest_id)}"
        )

    except Exception as exc:
        logger.error(
            f"[WS:CRASH] Unexpected error | contest={contest_id} | "
            f"client={client_host} | error={exc!r}",
            exc_info=True,
        )
        manager.disconnect(websocket, contest_id)
