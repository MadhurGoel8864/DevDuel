"""Bidding Service Layer — core business logic."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends
from redis.asyncio import Redis

from app.api.bidding.connection_manager import manager
from app.api.bidding.dao.bidding import BiddingDAO, get_bidding_dao
from app.api.contests.dao.contests import ContestDAO, get_contest_dao
from app.api.teams.dao.teams import TeamMemberDAO, get_team_member_dao
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


class BiddingService:
    """Business logic for the bidding system."""

    def __init__(
        self,
        dao: BiddingDAO,
        redis: Redis,
        contest_dao: ContestDAO,
        member_dao: TeamMemberDAO,
    ):
        self._dao = dao
        self._redis = redis
        self._contest_dao = contest_dao
        self._member_dao = member_dao

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
        # 1. Validate contest
        contest = await self._contest_dao.get_by_id(contest_id)
        if not contest:
            raise ContestNotFoundException(contest_id=contest_id)
        if contest.status != ContestStatus.ACTIVE:
            raise RegistrationClosedException(contest_id=contest_id)

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

        # 5. Seed Redis state
        await self._redis.set(_bid_key(auction.id), auction.base_price)
        await self._redis.set(_team_key(auction.id), "")

        logger.info(
            f"Auction {auction.id} started for problem {cp.id} in contest {contest_id}"
        )

        # 6. Schedule automatic finish after the timer expires
        asyncio.create_task(
            self._schedule_auto_finish(
                auction_id=auction.id,
                contest_id=contest_id,
                delay=duration_seconds,
            )
        )

        # 7. Notify all connected clients that a new auction has started
        await manager.broadcast(
            contest_id,
            {
                "type": "AUCTION_STARTED",
                "auction_id": auction.id,
                "contest_problem_id": auction.contest_problem_id,
                "base_price": auction.base_price,
                "start_time": (
                    auction.start_time.isoformat() if auction.start_time else None
                ),
                "end_time": auction.end_time.isoformat() if auction.end_time else None,
            },
        )

        return auction

    async def _schedule_auto_finish(
        self, auction_id: str, contest_id: str, delay: int
    ) -> None:
        """
        Background coroutine: waits `delay` seconds then auto-finishes the auction
        and broadcasts the result to all connected WebSocket clients.

        If the auction was already manually finished before the timer fires,
        `finish_auction()` is idempotent — the DB row is already FINISHED so
        the Redis keys are gone and it returns cleanly.
        """
        await asyncio.sleep(delay)
        try:
            logger.info(f"Auto-finishing auction {auction_id} after {delay}s")
            assignment = await self.finish_auction(auction_id)
            await manager.broadcast(
                contest_id,
                {
                    "type": "AUCTION_FINISHED",
                    "auction_id": auction_id,
                    "winning_team_id": assignment.team_id if assignment else None,
                    "winning_bid": assignment.winning_bid if assignment else None,
                },
            )
        except Exception as exc:
            logger.error(f"Auto-finish failed for auction {auction_id}: {exc}")

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
        lock_identifier = f"{team_id}:{amount}"

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
            current_highest = int(await self._redis.get(_bid_key(auction_id)) or 0)
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

        logger.info(
            f"New highest bid: team={team_id}, amount={amount}, auction={auction_id}"
        )
        return {"team_id": team_id, "amount": amount}

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

        # 1. Read from Redis
        highest_bid_raw = await self._redis.get(_bid_key(auction_id))
        highest_team_raw = await self._redis.get(_team_key(auction_id))

        winning_bid = int(highest_bid_raw) if highest_bid_raw else None
        winning_team_id = (
            highest_team_raw.decode()
            if isinstance(highest_team_raw, bytes)
            else highest_team_raw
        ) or None

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
) -> BiddingService:
    return BiddingService(
        dao=dao,
        redis=redis,
        contest_dao=contest_dao,
        member_dao=member_dao,
    )
