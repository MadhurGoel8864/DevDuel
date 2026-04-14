"""
Auction Scheduler — owns background timers that auto-finish auctions.

Problem this solves:
    start_auction() used to schedule auto-finish via asyncio.create_task(self.
    _schedule_auto_finish(...)). That captured a request-scoped AsyncSession,
    which was already closed by the time the timer fired, so finish_auction
    silently failed and the auction was stuck ACTIVE forever. The task
    reference was also dropped (CPython holds only weak refs to tasks), so
    GC could cancel the timer mid-sleep. There was no recovery on restart.

Design:
    - Module-level singleton (`auction_scheduler`).
    - `start(app)`  — called from FastAPI lifespan; runs a recovery sweep
                      that finalizes auctions whose end_time is already in
                      the past and reschedules future ones.
    - `schedule()`  — sleeps until wall-clock end_time (not a fixed delay),
                      stores a strong task ref in `_tasks`, and then calls
                      `_run_finish` on expiry.
    - `cancel()`    — used by force_end_auction to avoid a double broadcast.
    - `_run_finish` — opens its own AsyncSession and invokes finish_auction.

All DB work goes through a fresh `AsyncSessionLocal()`; the Redis client is
the global one from `app.core.redis.get_redis()`.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.api.bidding.dao.bidding import BiddingDAO
from app.api.bidding.services.event_bus import fanout_bidding_event
from app.api.contests.dao.contests import ContestDAO, TeamContestDAO
from app.api.teams.dao.teams import TeamDAO, TeamMemberDAO
from app.core.database import AsyncSessionLocal
from app.core.enums import AuctionStatus
from app.core.redis import get_redis
from app.database.models.bidding import ProblemAuction

logger = logging.getLogger(__name__)

# Hard cap on how long the DB side of finish_auction can take.
# The work is a couple of SELECTs + one transactional UPDATE; 5s is
# generous while still catching a stuck session quickly.
_FINISH_TIMEOUT_SECONDS = 5.0


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class AuctionScheduler:
    """Background scheduler for auto-finishing auctions.

    Thread-safety note: AsyncIO is single-threaded per event loop, so plain
    dict access is fine for `_tasks`. We keep a strong reference to every
    pending task to protect it from garbage collection.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}
        self._started: bool = False

    # ── Public API ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Run the recovery sweep on application startup."""
        if self._started:
            return
        self._started = True
        try:
            await self._recover_auctions()
        except Exception as exc:  # defensive — never block app startup
            logger.error(f"[scheduler] recovery sweep failed: {exc!r}", exc_info=True)

    async def stop(self) -> None:
        """Cancel all pending timers on application shutdown."""
        for task in list(self._tasks.values()):
            if not task.done():
                task.cancel()
        self._tasks.clear()

    def schedule(self, auction_id: str, contest_id: str, end_time: datetime) -> None:
        """Schedule `auction_id` to auto-finish at `end_time` (wall clock)."""
        # Cancel any pre-existing timer for the same auction (defensive —
        # should not normally happen).
        existing = self._tasks.get(auction_id)
        if existing and not existing.done():
            existing.cancel()

        task = asyncio.create_task(
            self._wait_and_finish(auction_id, contest_id, end_time),
            name=f"auction-finish-{auction_id}",
        )
        self._tasks[auction_id] = task
        # Clean up the strong reference once the task completes so the dict
        # doesn't grow unbounded.
        task.add_done_callback(lambda _t, aid=auction_id: self._tasks.pop(aid, None))
        logger.info(
            f"[scheduler] scheduled auction {auction_id} to finish at "
            f"{end_time.isoformat()}"
        )

    def cancel(self, auction_id: str) -> None:
        """Cancel a pending auto-finish timer (used when force-ending)."""
        task = self._tasks.pop(auction_id, None)
        if task and not task.done():
            task.cancel()
            logger.info(f"[scheduler] cancelled timer for auction {auction_id}")

    # ── Internal ───────────────────────────────────────────────────────────

    async def _wait_and_finish(
        self, auction_id: str, contest_id: str, end_time: datetime
    ) -> None:
        """Sleep until `end_time`, then finalize the auction.

        Uses wall-clock comparison rather than a fixed delay so clock drift
        or rescheduling can't leave the auction outliving its own deadline.
        """
        try:
            now = datetime.now(tz=timezone.utc)
            delay = (end_time - now).total_seconds()
            if delay > 0:
                await asyncio.sleep(delay)
            await self._run_finish(auction_id, contest_id)
        except asyncio.CancelledError:
            # Normal path when force-end cancels the timer; swallow silently.
            logger.debug(f"[scheduler] timer for auction {auction_id} cancelled")
            raise
        except Exception as exc:
            logger.error(
                f"[scheduler] _wait_and_finish failed for {auction_id}: {exc!r}",
                exc_info=True,
            )

    async def _run_finish(self, auction_id: str, contest_id: str) -> None:
        """Open a fresh DB session, finalize the auction, and broadcast."""
        logger.info(f"[scheduler] finalizing auction {auction_id}")
        redis = await get_redis()
        try:
            async with AsyncSessionLocal() as session:
                # Lazy import to avoid circular dependency with the service
                # module that pulls in this scheduler on module load.
                from app.api.bidding.services.bidding import BiddingService

                dao = BiddingDAO(session)
                svc = BiddingService(
                    dao=dao,
                    redis=redis,
                    contest_dao=ContestDAO(session),
                    member_dao=TeamMemberDAO(session),
                    team_dao=TeamDAO(session),
                    team_contest_dao=TeamContestDAO(session),
                )
                assignment = await asyncio.wait_for(
                    svc.finish_auction(auction_id),
                    timeout=_FINISH_TIMEOUT_SECONDS,
                )
                finished = await dao.get_auction_by_id(auction_id)
        except asyncio.TimeoutError:
            logger.error(
                f"[scheduler] finish_auction timed out after "
                f"{_FINISH_TIMEOUT_SECONDS}s for auction {auction_id}"
            )
            return
        except Exception as exc:
            logger.error(
                f"[scheduler] finish_auction raised for {auction_id}: {exc!r}",
                exc_info=True,
            )
            return

        # If assignment is None we may still have a valid no-winner finish.
        # Only broadcast if `finished` exists and is FINISHED — this avoids
        # clobbering a race where force_end_auction already ran and marked
        # the auction FINISHED before us; in that case finish_auction's
        # "already FINISHED" guard returned None, and force_end_auction has
        # already broadcast the authoritative result.
        if finished is None or finished.status != AuctionStatus.FINISHED:
            return
        if assignment is None and finished.winning_team_id is not None:
            # Some other code path already finalized this auction — don't
            # double-broadcast.
            return
        await fanout_bidding_event(
            contest_id=contest_id,
            payload={
                "type": "AUCTION_FINISHED",
                "server_time": _now_iso(),
                "auction_id": auction_id,
                "contest_problem_id": finished.contest_problem_id,
                "winning_team_id": assignment.team_id if assignment else None,
                "winning_bid": assignment.winning_bid if assignment else None,
            },
        )

    async def _recover_auctions(self) -> None:
        """Startup sweep: finalize past auctions, reschedule future ones."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ProblemAuction).where(
                    ProblemAuction.status == AuctionStatus.ACTIVE
                )
            )
            active_auctions = list(result.scalars().all())

        if not active_auctions:
            logger.info("[scheduler] recovery: no ACTIVE auctions found")
            return

        now = datetime.now(tz=timezone.utc)
        finalized = 0
        rescheduled = 0
        for auction in active_auctions:
            end_time = _as_utc(auction.end_time)
            if end_time is None or end_time <= now:
                # Already expired — finalize immediately.
                await self._run_finish(auction.id, auction.contest_id)
                finalized += 1
            else:
                self.schedule(auction.id, auction.contest_id, end_time)
                rescheduled += 1

        logger.info(
            f"[scheduler] recovery complete: finalized={finalized} "
            f"rescheduled={rescheduled}"
        )


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Return `dt` as a timezone-aware UTC datetime, or None.

    Postgres may hand back naïve timestamps depending on driver config; we
    normalize here so the `end_time - now` subtraction never blows up with
    a mixed tz error.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# Module-level singleton — import this instead of instantiating locally.
auction_scheduler = AuctionScheduler()
