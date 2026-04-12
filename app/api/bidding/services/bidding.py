"""Bidding Service Layer — core business logic."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends
from redis.asyncio import Redis

from app.api.bidding.connection_manager import manager
from app.api.bidding.dao.bidding import BiddingDAO, get_bidding_dao
from app.api.bidding.services.auction_scheduler import auction_scheduler
from app.api.contests.dao.contests import (
    ContestDAO,
    TeamContestDAO,
    get_contest_dao,
    get_team_contest_dao,
)
from app.api.teams.dao.teams import (
    TeamDAO,
    TeamMemberDAO,
    get_team_dao,
    get_team_member_dao,
)
from app.core.enums import AuctionStatus, ContestStatus, TeamRole
from app.core.exceptions.bidding import (
    AuctionAlreadyActiveException,
    AuctionExpiredException,
    AuctionNotActiveException,
    AuctionNotFoundException,
    BidTooLowException,
    InsufficientCurrencyException,
    NoProblemAvailableException,
    NotBidderRoleException,
    TeamNotInContestException,
)
from app.core.exceptions.auth import ForbiddenException
from app.core.exceptions.contests import (
    ContestNotFoundException,
    RegistrationClosedException,
)
from app.core.redis import get_redis_client
from app.database.models.bidding import ContestProblemAssignment, ProblemAuction

logger = logging.getLogger(__name__)

# ── Redis key helpers ──────────────────────────────────────────────────────────

_HIGHEST_BID_KEY = "auction:{auction_id}:highest_bid"
_HIGHEST_TEAM_KEY = "auction:{auction_id}:highest_team"
_LOCK_KEY = "auction:{auction_id}:lock"
_LOCK_TTL = 5  # seconds — lock auto-expires to prevent deadlocks


def _bid_key(auction_id: str) -> str:
    return _HIGHEST_BID_KEY.format(auction_id=auction_id)


def _team_key(auction_id: str) -> str:
    return _HIGHEST_TEAM_KEY.format(auction_id=auction_id)


def _lock_key(auction_id: str) -> str:
    return _LOCK_KEY.format(auction_id=auction_id)


def _now_iso() -> str:
    """Return current UTC time as an ISO-8601 string for WS payloads."""
    return datetime.now(tz=timezone.utc).isoformat()


class BiddingService:
    """Business logic for the bidding system."""

    def __init__(
        self,
        dao: BiddingDAO,
        redis: Redis,
        contest_dao: ContestDAO,
        member_dao: TeamMemberDAO,
        team_dao: TeamDAO,
        team_contest_dao: TeamContestDAO,
    ):
        self._dao = dao
        self._redis = redis
        self._contest_dao = contest_dao
        self._member_dao = member_dao
        self._team_dao = team_dao
        self._team_contest_dao = team_contest_dao

    # ── Start Auction ──────────────────────────────────────────────────────────

    async def start_auction(
        self,
        contest_id: str,
        contest_problem_id: Optional[str],
        duration_seconds: int,
        requesting_user_id: str,
    ) -> ProblemAuction:
        """
        Start an auction for the next problem in a contest.

        Steps:
        1. Validate contest exists and is ACTIVE.
        2. Validate no other auction is currently ACTIVE.
        3. Resolve the target ContestProblem (explicit or next by problem_order).
        4. Create the ProblemAuction DB row.
        5. Seed Redis with the starting bid state.

        Raises:
            ContestNotFoundException: Contest does not exist.
            RegistrationClosedException: Contest is not ACTIVE.
            AuctionAlreadyActiveException: Another auction is already running.
            NoProblemAvailableException: No remaining problems to auction.
        """
        # 0. Validate duration bounds (defensive — schema also enforces)
        if duration_seconds < 10 or duration_seconds > 600:
            from app.core.exceptions.common import BadRequestException

            raise BadRequestException(
                message="duration_seconds must be between 10 and 600"
            )

        # 1. Validate contest
        contest = await self._contest_dao.get_by_id(contest_id)
        if not contest:
            raise ContestNotFoundException(contest_id=contest_id)
        if contest.status != ContestStatus.ACTIVE:
            raise RegistrationClosedException(contest_id=contest_id)

        # 1b. Only the contest organizer can start auctions
        if contest.created_by != requesting_user_id:
            raise ForbiddenException(
                message="Only the contest organizer can start auctions"
            )

        # 2. Guard — only one active auction per contest
        existing_active = await self._dao.get_active_auction_for_contest(contest_id)
        if existing_active:
            raise AuctionAlreadyActiveException(contest_id=contest_id)

        # 3. Resolve target problem
        if contest_problem_id:
            # Use the provided problem — still validate it belongs to the contest
            # by relying on fetch_next_problem's ownership check; for an explicit
            # id we load via the DAO's next-problem query filtered to that id.
            # Simple approach: trust the provided id; the UNIQUE constraint on
            # problem_auctions.contest_problem_id will prevent double-auctioning.
            from sqlalchemy import select

            from app.database.models.problems import ContestProblem

            result = await self._dao._session.execute(
                select(ContestProblem).where(
                    ContestProblem.id == contest_problem_id,
                    ContestProblem.contest_id == contest_id,
                    ContestProblem.is_active.is_(True),
                )
            )
            cp = result.scalar_one_or_none()
        else:
            cp = await self._dao.fetch_next_problem(contest_id)

        if not cp:
            raise NoProblemAvailableException(contest_id=contest_id)

        # 4. Create auction row
        now = datetime.now(tz=timezone.utc)
        end_time = now + timedelta(seconds=duration_seconds)
        auction = await self._dao.create_auction(
            contest_id=contest_id,
            contest_problem_id=cp.id,
            base_price=cp.problem.base_price,
            start_time=now,
            end_time=end_time,
        )

        # 5. Seed Redis state. If Redis is down, roll the auction row back
        #    to FINISHED-no-winner so we never leave a dangling ACTIVE row
        #    that bids will target with a fallback-of-zero highest.
        try:
            await self._redis.set(_bid_key(auction.id), auction.base_price)
            await self._redis.set(_team_key(auction.id), "")
        except Exception as exc:
            logger.error(
                f"Redis seed failed for auction {auction.id}; rolling back: {exc!r}"
            )
            try:
                await self._dao.finish_auction_atomic(
                    auction_id=auction.id,
                    winning_team_id=None,
                    winning_bid=None,
                    contest_id=contest_id,
                    contest_problem_id=cp.id,
                    end_time=datetime.now(tz=timezone.utc),
                )
            except Exception as rollback_exc:
                logger.error(
                    f"Rollback to FINISHED failed for auction {auction.id}: "
                    f"{rollback_exc!r}"
                )
            from app.core.exceptions.common import BadRequestException

            raise BadRequestException(
                message="Failed to initialize auction state. Please try again."
            )

        logger.info(
            f"Auction {auction.id} started for problem {cp.id} in contest {contest_id}"
        )

        # 6. Schedule automatic finish at the wall-clock end_time. The
        #    scheduler owns its own DB session so the request-scoped session
        #    is free to close when this handler returns.
        auction_scheduler.schedule(
            auction_id=auction.id,
            contest_id=contest_id,
            end_time=end_time,
        )

        # 7. Notify all connected clients that a new auction has started
        auction_payload = await self.enrich_auction(auction)
        # ISO-format datetimes for JSON
        for key in ("start_time", "end_time", "created_at", "updated_at"):
            if auction_payload.get(key) is not None and hasattr(
                auction_payload[key], "isoformat"
            ):
                auction_payload[key] = auction_payload[key].isoformat()
        if hasattr(auction_payload.get("status"), "value"):
            auction_payload["status"] = auction_payload["status"].value

        await manager.broadcast(
            contest_id,
            {
                "type": "AUCTION_STARTED",
                "server_time": _now_iso(),
                "auction": auction_payload,
            },
        )

        return auction

    # ── Live State Enrichment ───────────────────────────────────────────────────

    async def get_live_bid_state(self, auction_id: str) -> dict:
        """
        Read the current highest bid and team from Redis for an active auction.

        Returns:
            dict with current_highest_bid (int|None) and current_highest_team (str|None).
        """
        highest_bid_raw = await self._redis.get(_bid_key(auction_id))
        highest_team_raw = await self._redis.get(_team_key(auction_id))

        current_bid = int(highest_bid_raw) if highest_bid_raw else None
        current_team = highest_team_raw or None

        return {
            "current_highest_bid": current_bid,
            "current_highest_team": current_team,
        }

    async def get_sync_payload(self, contest_id: str) -> dict:
        """
        Build the SYNC payload sent to a (re)connecting WebSocket client.

        Includes the current active auction (enriched with live Redis state)
        and the contest's status so the client can rebuild its UI.
        """
        contest = await self._contest_dao.get_by_id(contest_id)
        contest_status = contest.status.value if contest and hasattr(
            contest.status, "value"
        ) else (contest.status if contest else None)

        current_auction_payload = None
        try:
            current_auction = await self.get_current_auction(contest_id=contest_id)
        except Exception:
            current_auction = None

        if current_auction and current_auction.status == AuctionStatus.ACTIVE:
            current_auction_payload = await self.enrich_auction(current_auction)
            for key in ("start_time", "end_time", "created_at", "updated_at"):
                val = current_auction_payload.get(key)
                if val is not None and hasattr(val, "isoformat"):
                    current_auction_payload[key] = val.isoformat()
            if hasattr(current_auction_payload.get("status"), "value"):
                current_auction_payload["status"] = current_auction_payload[
                    "status"
                ].value

        return {
            "contest_status": contest_status,
            "current_auction": current_auction_payload,
        }

    async def enrich_auction(self, auction: ProblemAuction) -> dict:
        """
        Convert a ProblemAuction ORM object to a dict, enriching ACTIVE auctions
        with live bid data from Redis.

        For ACTIVE auctions only `current_highest_bid` / `current_highest_team`
        are populated — `winning_bid` / `winning_team_id` stay None until the
        auction is actually FINISHED. Mirroring the live leader into the
        `winning_*` fields caused clients that read `winning_bid` to
        prematurely render an in-progress auction as already-won.
        """
        from app.api.bidding.schemas.bidding import AuctionResponseData

        data = AuctionResponseData.model_validate(auction).model_dump()

        if auction.status == AuctionStatus.ACTIVE:
            live = await self.get_live_bid_state(auction.id)
            data["current_highest_bid"] = live["current_highest_bid"]
            data["current_highest_team"] = live["current_highest_team"]
            # winning_* intentionally left as whatever the DB row has
            # (None for a fresh ACTIVE auction).

        return data

    # ── List All Auctions ──────────────────────────────────────────────────────

    async def get_all_auctions(
        self, contest_id: str, requesting_user_id: str
    ) -> list[ProblemAuction]:
        """
        Return all auctions for a contest, ordered by created_at ASC.

        Raises:
            ContestNotFoundException: If the contest does not exist.
            ForbiddenException: If the user has no relation to this contest.
        """
        contest = await self._contest_dao.get_by_id(contest_id)
        if not contest:
            raise ContestNotFoundException(contest_id=contest_id)

        is_organizer = contest.created_by == requesting_user_id
        if not is_organizer:
            in_contest = await self._team_contest_dao.is_user_in_contest(
                contest_id, requesting_user_id
            )
            if not in_contest:
                raise ForbiddenException(
                    message="You do not have access to this contest's auctions"
                )

        return await self._dao.get_all_auctions_for_contest(contest_id)

    # ── Get Current Auction ────────────────────────────────────────────────────

    async def get_current_auction(self, contest_id: str) -> ProblemAuction:
        """
        Return the currently ACTIVE auction for a contest.
        Falls back to the most recent auction if none is active.

        Raises:
            AuctionNotFoundException: If no auction exists for this contest.
        """
        auction = await self._dao.get_active_auction_for_contest(contest_id)
        if not auction:
            auction = await self._dao.get_latest_auction_for_contest(contest_id)
        if not auction:
            raise AuctionNotFoundException(
                message=f"No auction found for contest '{contest_id}'"
            )
        return auction

    # ── Place Bid ─────────────────────────────────────────────────────────────

    async def place_bid(
        self,
        auction_id: str,
        team_id: str,
        user_id: str,
        amount: int,
    ) -> dict:
        """
        Place a bid on an active auction.

        Steps:
        1. Validate auction exists and is ACTIVE.
        2. Validate user is a BIDDING-role member of the team.
        3. Validate team's currency >= amount.
        4. Acquire Redis lock.
        5. Validate amount > current highest bid (re-read under lock).
        6. Update Redis highest bid and team.
        7. Persist bid to the database.

        Returns:
            dict with keys: team_id, amount (for broadcasting).

        Raises:
            AuctionNotFoundException
            AuctionNotActiveException
            NotBidderRoleException
            InsufficientCurrencyException
            BidTooLowException
        """
        # 1. Validate auction
        auction = await self._dao.get_auction_by_id(auction_id)
        if not auction:
            raise AuctionNotFoundException(auction_id=auction_id)
        if auction.status != AuctionStatus.ACTIVE:
            raise AuctionNotActiveException(auction_id=auction_id)

        # 2. Reject bids placed after the auction end_time
        if auction.end_time and datetime.now(tz=timezone.utc) > auction.end_time:
            raise AuctionExpiredException(auction_id=auction_id)

        # 3. Validate bidder role
        member = await self._member_dao.get(team_id=team_id, user_id=user_id)
        if not member or member.role != TeamRole.BIDDING:
            raise NotBidderRoleException(user_id=user_id, team_id=team_id)

        # 4. Validate team is registered in this contest
        team_contest = await self._dao.get_team_contest(
            team_id=team_id, contest_id=auction.contest_id
        )
        if not team_contest:
            raise TeamNotInContestException(
                team_id=team_id, contest_id=auction.contest_id
            )

        # 5. Validate team has enough currency
        if team_contest.currency < amount:
            raise InsufficientCurrencyException(
                team_id=team_id,
                required=amount,
                available=team_contest.currency,
            )

        # 4–6. Redis lock → check → update
        lock_key = _lock_key(auction_id)
        lock_identifier = str(uuid.uuid4())

        # SET NX EX — acquire lock; if already held, reject immediately (no spin-wait)
        acquired = await self._redis.set(
            lock_key, lock_identifier, nx=True, ex=_LOCK_TTL
        )
        if not acquired:
            from app.core.exceptions.common import BadRequestException

            raise BadRequestException(
                message="Another bid is being processed. Please retry in a moment."
            )

        try:
            # Re-read the auction *under the lock* so a concurrent
            # finish_auction() cannot sneak a bid into a FINISHED row.
            fresh = await self._dao.get_auction_by_id(auction_id)
            if not fresh or fresh.status != AuctionStatus.ACTIVE:
                raise AuctionNotActiveException(auction_id=auction_id)
            if fresh.end_time and datetime.now(tz=timezone.utc) > fresh.end_time:
                raise AuctionExpiredException(auction_id=auction_id)

            # If the Redis keys are gone, the auction has already been
            # finalized (or never seeded); do NOT fall back to 0 — that
            # would let any positive bid sneak into a FINISHED auction.
            highest_raw = await self._redis.get(_bid_key(auction_id))
            if highest_raw is None:
                raise AuctionNotActiveException(auction_id=auction_id)
            current_highest = int(highest_raw)
            if amount <= current_highest:
                raise BidTooLowException(
                    bid_amount=amount, current_highest=current_highest
                )

            # Update Redis
            await self._redis.set(_bid_key(auction_id), amount)
            await self._redis.set(_team_key(auction_id), team_id)
        finally:
            # Always release the lock
            current_lock = await self._redis.get(lock_key)
            if current_lock == lock_identifier:
                await self._redis.delete(lock_key)

        # 7. Persist bid to DB (now includes user_id)
        await self._dao.insert_bid(
            auction_id=auction_id,
            team_id=team_id,
            user_id=user_id,
            bid_amount=amount,
        )

        # Fetch team name for the broadcast (avoids N+1 fetches on every client)
        team = await self._team_dao.get_by_id(team_id)
        team_name = team.name if team else None

        logger.info(
            f"New highest bid: team={team_id} ({team_name}), amount={amount}, auction={auction_id}"
        )
        return {"team_id": team_id, "team_name": team_name, "amount": amount}

    # ── Finish Auction ─────────────────────────────────────────────────────────

    async def finish_auction(self, auction_id: str) -> ContestProblemAssignment | None:
        """
        Finalise an auction (called when the timer ends or manually triggered).

        Steps:
        1. Read highest bid and team from Redis.
        2. Update ProblemAuction → FINISHED with winner.
        3. If there is a winner: deduct currency, create assignment.
        4. Clean up Redis keys.

        Returns:
            ContestProblemAssignment if a winner exists, else None.

        Raises:
            AuctionNotFoundException
        """
        auction = await self._dao.get_auction_by_id(auction_id)
        if not auction:
            raise AuctionNotFoundException(auction_id=auction_id)

        # Guard: already finished — return existing result without overwriting
        if auction.status == AuctionStatus.FINISHED:
            logger.info(f"Auction {auction_id} already finished, skipping")
            return None

        # 1. Read from Redis. The client is configured with
        #    decode_responses=True so values are always str | None.
        highest_bid_raw = await self._redis.get(_bid_key(auction_id))
        highest_team_raw = await self._redis.get(_team_key(auction_id))

        winning_team_id = highest_team_raw or None
        winning_bid = int(highest_bid_raw) if highest_bid_raw else None

        # No winner if no team has bid above base_price
        if not winning_team_id:
            winning_team_id = None
            winning_bid = None

        # 2–4. Single atomic DB transaction: mark FINISHED + deduct + assign
        assignment = await self._dao.finish_auction_atomic(
            auction_id=auction_id,
            winning_team_id=winning_team_id,
            winning_bid=winning_bid,
            contest_id=auction.contest_id,
            contest_problem_id=auction.contest_problem_id,
        )

        if winning_team_id:
            logger.info(
                f"Auction {auction_id} won by team={winning_team_id} for {winning_bid}"
            )
        else:
            logger.info(f"Auction {auction_id} ended with no winner")

        # 5. Clean up Redis state
        await self._redis.delete(
            _bid_key(auction_id),
            _team_key(auction_id),
            _lock_key(auction_id),
        )

        return assignment

    # ── Force End Auction ──────────────────────────────────────────────────────

    async def force_end_auction(
        self, auction_id: str, requesting_user_id: str
    ) -> ProblemAuction:
        """
        Immediately end an ACTIVE auction (organizer-only).

        Steps:
        1. Validate auction exists.
        2. Validate caller is the contest organizer.
        3. Validate auction is ACTIVE.
        4. Read current highest bid from Redis.
        5. Atomically finish the auction with end_time = now().
        6. Clean up Redis keys.
        7. Broadcast AUCTION_FINISHED via WebSocket.

        Raises:
            AuctionNotFoundException: Auction does not exist.
            ForbiddenException: Caller is not the contest organizer.
            AuctionNotActiveException: Auction is not currently ACTIVE.
        """
        auction = await self._dao.get_auction_by_id(auction_id)
        if not auction:
            raise AuctionNotFoundException(auction_id=auction_id)

        contest = await self._contest_dao.get_by_id(auction.contest_id)
        if not contest:
            raise ContestNotFoundException(contest_id=auction.contest_id)

        if contest.created_by != requesting_user_id:
            raise ForbiddenException(
                message="Only the contest organizer can force-end an auction"
            )

        if auction.status != AuctionStatus.ACTIVE:
            raise AuctionNotActiveException(auction_id=auction_id)

        # Cancel the auto-finish timer before finalizing so the scheduler
        # can't wake up and broadcast a duplicate AUCTION_FINISHED with
        # winning_bid=None on top of our authoritative one.
        auction_scheduler.cancel(auction_id)

        # Read winner from Redis (client uses decode_responses=True, so
        # values are always str | None).
        highest_bid_raw = await self._redis.get(_bid_key(auction_id))
        highest_team_raw = await self._redis.get(_team_key(auction_id))

        winning_team_id = highest_team_raw or None
        winning_bid = int(highest_bid_raw) if highest_bid_raw else None

        if not winning_team_id:
            winning_team_id = None
            winning_bid = None

        now = datetime.now(tz=timezone.utc)
        await self._dao.finish_auction_atomic(
            auction_id=auction_id,
            winning_team_id=winning_team_id,
            winning_bid=winning_bid,
            contest_id=auction.contest_id,
            contest_problem_id=auction.contest_problem_id,
            end_time=now,
        )

        await self._redis.delete(
            _bid_key(auction_id),
            _team_key(auction_id),
            _lock_key(auction_id),
        )

        await manager.broadcast(
            auction.contest_id,
            {
                "type": "AUCTION_FINISHED",
                "server_time": _now_iso(),
                "auction_id": auction_id,
                "contest_problem_id": auction.contest_problem_id,
                "winning_team_id": winning_team_id,
                "winning_bid": winning_bid if winning_bid is not None else 0,
            },
        )

        logger.info(
            f"Auction {auction_id} force-ended by organizer={requesting_user_id} | "
            f"winner={winning_team_id!r} | winning_bid={winning_bid!r}"
        )

        return await self._dao.get_auction_by_id(auction_id)

    # ── Get Auction Result ─────────────────────────────────────────────────────

    async def get_auction_result(self, auction_id: str) -> ProblemAuction:
        """
        Return the final state of an auction.

        Raises:
            AuctionNotFoundException: If auction does not exist.
        """
        auction = await self._dao.get_auction_by_id(auction_id)
        if not auction:
            raise AuctionNotFoundException(auction_id=auction_id)
        return auction


# ── Dependency ─────────────────────────────────────────────────────────────────


async def get_bidding_service(
    dao: BiddingDAO = Depends(get_bidding_dao),
    redis: Redis = Depends(get_redis_client),
    contest_dao: ContestDAO = Depends(get_contest_dao),
    member_dao: TeamMemberDAO = Depends(get_team_member_dao),
    team_dao: TeamDAO = Depends(get_team_dao),
    team_contest_dao: TeamContestDAO = Depends(get_team_contest_dao),
) -> BiddingService:
    return BiddingService(
        dao=dao,
        redis=redis,
        contest_dao=contest_dao,
        member_dao=member_dao,
        team_dao=team_dao,
        team_contest_dao=team_contest_dao,
    )
