"""Bidding Data Access Object — raw database queries only."""

import logging
from typing import Optional

from fastapi import Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.enums import AssignmentStatus, AuctionStatus
from app.database.models.bidding import Bid, ContestProblemAssignment, ProblemAuction
from app.database.models.contests import TeamContest
from app.database.models.problems import ContestProblem

logger = logging.getLogger(__name__)


class BiddingDAO:
    """Data Access Object for all bidding-related database operations."""

    def __init__(self, session: AsyncSession):
        self._session = session

    # ── Auction ────────────────────────────────────────────────────────────────

    async def create_auction(
        self,
        contest_id: str,
        contest_problem_id: str,
        base_price: int,
        start_time: object,
        end_time: object,
    ) -> ProblemAuction:
        """Insert a new ProblemAuction row with status=ACTIVE."""
        try:
            auction = ProblemAuction(
                contest_id=contest_id,
                contest_problem_id=contest_problem_id,
                status=AuctionStatus.ACTIVE,
                base_price=base_price,
                start_time=start_time,
                end_time=end_time,
            )
            self._session.add(auction)
            await self._session.commit()
            await self._session.refresh(auction)
            logger.info(
                f"Auction created: {auction.id} for contest_problem {contest_problem_id}"
            )
            return auction
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to create auction: {e}")
            raise

    async def get_auction_by_id(self, auction_id: str) -> Optional[ProblemAuction]:
        """Fetch a ProblemAuction by primary key."""
        try:
            result = await self._session.execute(
                select(ProblemAuction).where(ProblemAuction.id == auction_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get auction {auction_id}: {e}")
            raise

    async def get_active_auction_for_contest(
        self, contest_id: str
    ) -> Optional[ProblemAuction]:
        """Return the single ACTIVE auction for a contest, or None."""
        try:
            result = await self._session.execute(
                select(ProblemAuction).where(
                    ProblemAuction.contest_id == contest_id,
                    ProblemAuction.status == AuctionStatus.ACTIVE,
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get active auction for contest {contest_id}: {e}")
            raise

    async def get_all_auctions_for_contest(
        self, contest_id: str
    ) -> list[ProblemAuction]:
        """Return all auctions for a contest, ordered by created_at ASC."""
        try:
            result = await self._session.execute(
                select(ProblemAuction)
                .where(ProblemAuction.contest_id == contest_id)
                .order_by(ProblemAuction.created_at.asc())
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get all auctions for contest {contest_id}: {e}")
            raise

    async def get_latest_auction_for_contest(
        self, contest_id: str
    ) -> Optional[ProblemAuction]:
        """Return the most recently created auction for a contest (any status)."""
        try:
            result = await self._session.execute(
                select(ProblemAuction)
                .where(ProblemAuction.contest_id == contest_id)
                .order_by(ProblemAuction.created_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get latest auction for contest {contest_id}: {e}")
            raise

    async def fetch_next_problem(self, contest_id: str) -> Optional[ContestProblem]:
        """
        Find the next ContestProblem for bidding.

        Selects the active ContestProblem with the lowest problem_order that
        does NOT yet have a finished auction (i.e. hasn't been resolved).
        """
        try:
            # Subquery: contest_problem_ids that already have a FINISHED auction
            finished_subq = (
                select(ProblemAuction.contest_problem_id).where(
                    ProblemAuction.contest_id == contest_id,
                    ProblemAuction.status == AuctionStatus.FINISHED,
                )
            ).scalar_subquery()

            result = await self._session.execute(
                select(ContestProblem)
                .where(
                    ContestProblem.contest_id == contest_id,
                    ContestProblem.is_active.is_(True),
                    ContestProblem.id.not_in(finished_subq),
                )
                .order_by(ContestProblem.problem_order.asc())
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to fetch next problem for contest {contest_id}: {e}")
            raise

    async def update_auction_result(
        self,
        auction_id: str,
        winning_team_id: Optional[str],
        winning_bid: Optional[int],
    ) -> Optional[ProblemAuction]:
        """Mark an auction as FINISHED with the given winner."""
        try:
            result = await self._session.execute(
                select(ProblemAuction).where(ProblemAuction.id == auction_id)
            )
            auction = result.scalar_one_or_none()
            if not auction:
                return None
            auction.status = AuctionStatus.FINISHED
            auction.winning_team_id = winning_team_id
            auction.winning_bid = winning_bid
            self._session.add(auction)
            await self._session.commit()
            await self._session.refresh(auction)
            logger.info(
                f"Auction {auction_id} finished. Winner: {winning_team_id}, bid: {winning_bid}"
            )
            return auction
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to update auction result {auction_id}: {e}")
            raise

    # ── Bids ───────────────────────────────────────────────────────────────────

    async def insert_bid(
        self, auction_id: str, team_id: str, user_id: str, bid_amount: int
    ) -> Bid:
        """Persist a bid row to the database, including the user who placed it."""
        try:
            bid = Bid(
                auction_id=auction_id,
                team_id=team_id,
                user_id=user_id,
                bid_amount=bid_amount,
            )
            self._session.add(bid)
            await self._session.commit()
            await self._session.refresh(bid)
            logger.info(
                f"Bid recorded: user={user_id}, team={team_id}, amount={bid_amount}, auction={auction_id}"
            )
            return bid
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to insert bid: {e}")
            raise

    # ── Team Currency ──────────────────────────────────────────────────────────

    async def get_team_contest(
        self, team_id: str, contest_id: str
    ) -> Optional[TeamContest]:
        """Fetch a TeamContest row for currency/score checks."""
        try:
            result = await self._session.execute(
                select(TeamContest).where(
                    TeamContest.team_id == team_id,
                    TeamContest.contest_id == contest_id,
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"Failed to get team_contest for team={team_id}, contest={contest_id}: {e}"
            )
            raise

    async def deduct_team_currency(
        self, team_id: str, contest_id: str, amount: int
    ) -> None:
        """Atomically deduct `amount` from team_contests.currency."""
        try:
            await self._session.execute(
                update(TeamContest)
                .where(
                    TeamContest.team_id == team_id,
                    TeamContest.contest_id == contest_id,
                )
                .values(currency=TeamContest.currency - amount)
            )
            await self._session.commit()
            logger.info(
                f"Deducted {amount} currency from team={team_id} in contest={contest_id}"
            )
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to deduct currency: {e}")
            raise

    # ── Atomic Auction Completion ──────────────────────────────────────────────

    async def finish_auction_atomic(
        self,
        auction_id: str,
        winning_team_id: Optional[str],
        winning_bid: Optional[int],
        contest_id: str,
        contest_problem_id: str,
        end_time: Optional[object] = None,
    ) -> Optional[ContestProblemAssignment]:
        """
        Finalize an auction in a single atomic transaction.

        Performs three operations inside one DB transaction:
          1. Mark ProblemAuction → FINISHED with winner info.
          2. Deduct winning_bid from the winning team's currency (only if winner exists).
          3. Create a ContestProblemAssignment for the winning team (only if winner exists).

        If any step raises an exception the entire transaction is rolled back —
        no partial state is ever committed.

        Returns:
            ContestProblemAssignment if a winner exists, else None.
        """
        try:
            # Step 1: Mark auction FINISHED
            result = await self._session.execute(
                select(ProblemAuction).where(ProblemAuction.id == auction_id)
            )
            auction = result.scalar_one_or_none()
            if not auction:
                return None

            # Guard: already finished — don't overwrite winner info
            if auction.status == AuctionStatus.FINISHED:
                logger.info(f"Auction {auction_id} already FINISHED, skipping atomic finish")
                return None

            auction.status = AuctionStatus.FINISHED
            auction.winning_team_id = winning_team_id
            auction.winning_bid = winning_bid
            if end_time is not None:
                auction.end_time = end_time
            self._session.add(auction)

            assignment: Optional[ContestProblemAssignment] = None

            if winning_team_id and winning_bid is not None:
                # Step 2: Deduct currency (single UPDATE, no separate commit)
                await self._session.execute(
                    update(TeamContest)
                    .where(
                        TeamContest.team_id == winning_team_id,
                        TeamContest.contest_id == contest_id,
                    )
                    .values(currency=TeamContest.currency - winning_bid)
                )

                # Step 3: Create assignment
                assignment = ContestProblemAssignment(
                    contest_id=contest_id,
                    contest_problem_id=contest_problem_id,
                    team_id=winning_team_id,
                    winning_bid=winning_bid,
                    status=AssignmentStatus.ASSIGNED,
                )
                self._session.add(assignment)

            # Single commit — all three ops succeed or all roll back
            await self._session.commit()

            if assignment:
                await self._session.refresh(assignment)

            logger.info(
                f"Auction {auction_id} atomically finished. "
                f"Winner: {winning_team_id}, bid: {winning_bid}"
            )
            return assignment

        except Exception as e:
            await self._session.rollback()
            logger.error(f"Atomic finish failed for auction {auction_id}: {e}")
            raise


# ── Dependency ─────────────────────────────────────────────────────────────────


async def get_bidding_dao(
    session: AsyncSession = Depends(get_db),
) -> BiddingDAO:
    return BiddingDAO(session)
