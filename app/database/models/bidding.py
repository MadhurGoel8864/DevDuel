"""Bidding-related SQLAlchemy models: ProblemAuction, Bid, ContestProblemAssignment."""

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import mapped_column, relationship

from app.core.enums import AssignmentStatus, AuctionStatus
from app.database.models.base import Base
from app.database.models.mixins import TimestampMixin
from app.database.utils import generate_uuid


class ProblemAuction(Base, TimestampMixin):
    """Represents the auction state for a single contest problem."""

    __tablename__ = "problem_auctions"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)

    contest_id = mapped_column(
        String(36),
        ForeignKey("contests.id", ondelete="CASCADE"),
        nullable=False,
    )

    contest_problem_id = mapped_column(
        String(36),
        ForeignKey("contest_problems.id", ondelete="CASCADE"),
        nullable=False,
    )

    status = mapped_column(
        Enum(AuctionStatus, name="auctionstatus"),
        default=AuctionStatus.PENDING,
        nullable=False,
    )

    base_price = mapped_column(Integer, nullable=False)
    start_time = mapped_column(DateTime(timezone=True), nullable=True)
    end_time = mapped_column(DateTime(timezone=True), nullable=True)

    winning_team_id = mapped_column(
        String(36),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    winning_bid = mapped_column(Integer, nullable=True)

    # Relationships
    bids = relationship(
        "Bid",
        back_populates="auction",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("contest_problem_id", name="uq_auction_contest_problem"),
        Index("ix_auction_contest_id", "contest_id"),
    )


class Bid(Base):
    """Stores every bid attempt within an auction."""

    __tablename__ = "bids"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)

    auction_id = mapped_column(
        String(36),
        ForeignKey("problem_auctions.id", ondelete="CASCADE"),
        nullable=False,
    )

    team_id = mapped_column(
        String(36),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # nullable so old rows don't break on migration
    )

    bid_amount = mapped_column(Integer, nullable=False)

    created_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.timezone("Asia/Kolkata", func.now()),
        nullable=False,
    )

    # Relationships
    auction = relationship("ProblemAuction", back_populates="bids")

    __table_args__ = (Index("ix_bid_auction_id", "auction_id"),)


class ContestProblemAssignment(Base, TimestampMixin):
    """Tracks which team won which problem in a contest."""

    __tablename__ = "contest_problem_assignments"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)

    contest_id = mapped_column(
        String(36),
        ForeignKey("contests.id", ondelete="CASCADE"),
        nullable=False,
    )

    contest_problem_id = mapped_column(
        String(36),
        ForeignKey("contest_problems.id", ondelete="CASCADE"),
        nullable=False,
    )

    team_id = mapped_column(
        String(36),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )

    winning_bid = mapped_column(Integer, nullable=False)

    status = mapped_column(
        Enum(AssignmentStatus, name="assignmentstatus"),
        default=AssignmentStatus.ASSIGNED,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("contest_problem_id", name="uq_assignment_contest_problem"),
        Index("ix_assignment_contest_id", "contest_id"),
        Index("ix_assignment_team_id", "team_id"),
    )
