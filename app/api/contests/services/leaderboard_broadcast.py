"""Helpers to compute and fanout LEADERBOARD_UPDATE events over the bidding
WebSocket channel. Called after any TeamContest score/currency mutation.
"""

import logging
from datetime import datetime, timezone

from app.api.bidding.services.event_bus import fanout_bidding_event
from app.api.contests.dao.contests import TeamContestDAO
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


async def _build_leaderboard_payload(contest_id: str) -> dict:
    """Compute the current leaderboard from a fresh session and wrap it in a
    LEADERBOARD_UPDATE envelope suitable for the bidding WS channel.
    """
    async with AsyncSessionLocal() as session:
        team_contest_dao = TeamContestDAO(session)
        registrations = (
            await team_contest_dao.get_active_registrations_by_contest(contest_id)
        )
        sorted_teams = sorted(
            registrations,
            key=lambda r: (r.score, r.currency),
            reverse=True,
        )
        name_by_team_id = dict(
            await team_contest_dao.get_registered_teams(contest_id)
        )

    entries = [
        {
            "rank": idx + 1,
            "team_id": tc.team_id,
            "team_name": name_by_team_id.get(tc.team_id, ""),
            "score": tc.score,
            "currency": tc.currency,
        }
        for idx, tc in enumerate(sorted_teams)
    ]

    return {
        "type": "LEADERBOARD_UPDATE",
        "server_time": _now_iso(),
        "entries": entries,
    }


async def broadcast_leaderboard(contest_id: str) -> None:
    """Fire-and-forget: compute and fanout the leaderboard. Swallows errors so
    callers can invoke this after a successful mutation without risking the
    main request path.
    """
    try:
        payload = await _build_leaderboard_payload(contest_id)
        await fanout_bidding_event(contest_id=contest_id, payload=payload)
    except Exception as exc:
        logger.warning(
            f"[leaderboard-broadcast] failed for contest={contest_id}: {exc!r}",
            exc_info=True,
        )
