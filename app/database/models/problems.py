"""Problem and ContestProblem SQLAlchemy models."""

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import mapped_column, relationship

from app.core.enums import Difficulty
from app.database.models.base import Base
from app.database.models.mixins import TimestampMixin
from app.database.utils import generate_uuid


class Problem(Base, TimestampMixin):
    """Reusable coding problem."""

    __tablename__ = "problems"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title = mapped_column(String(255), nullable=False)
    slug = mapped_column(String(300), nullable=False, unique=True)
    description = mapped_column(Text, nullable=False)
    difficulty = mapped_column(
        Enum(
            Difficulty,
            name="difficulty",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        nullable=False,
    )
    points = mapped_column(Integer, nullable=False)
    base_price = mapped_column(Integer, nullable=False)
    time_limit_ms = mapped_column(Integer, default=2000, nullable=False)
    memory_limit_mb = mapped_column(Integer, default=256, nullable=False)

    created_by = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    is_active = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    contest_problems = relationship(
        "ContestProblem",
        back_populates="problem",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_problem_difficulty", "difficulty"),
        Index("ix_problem_slug", "slug", unique=True),
    )


class ContestProblem(Base):
    """Maps a Problem to a Contest and determines bidding order."""

    __tablename__ = "contest_problems"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)

    contest_id = mapped_column(
        String(36),
        ForeignKey("contests.id", ondelete="CASCADE"),
        nullable=False,
    )
    problem_id = mapped_column(
        String(36),
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
    )
    problem_order = mapped_column(Integer, nullable=False)
    is_active = mapped_column(Boolean, default=True, nullable=False)

    created_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.timezone("Asia/Kolkata", func.now()),
        nullable=False,
    )

    # Relationships
    contest = relationship("Contest", back_populates="problems", lazy="selectin")
    problem = relationship(
        "Problem", back_populates="contest_problems", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("contest_id", "problem_id", name="uq_contest_problem"),
        UniqueConstraint(
            "contest_id", "problem_order", name="uq_contest_problem_order"
        ),
        Index("ix_contest_problem_contest_id", "contest_id"),
        Index("ix_contest_problem_problem_id", "problem_id"),
    )
