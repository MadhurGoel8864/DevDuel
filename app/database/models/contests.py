from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import mapped_column, relationship

from app.database.models.base import Base
from app.database.models.mixins import TimestampMixin
from app.database.utils import generate_uuid


class Contest(Base, TimestampMixin):
    __tablename__ = "contests"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name = mapped_column(String(100), nullable=False)
    description = mapped_column(String(255), nullable=True)

    start_time = mapped_column(DateTime, nullable=False)
    end_time = mapped_column(DateTime, nullable=False)

    is_active = mapped_column(Boolean, default=True, nullable=False)

    teams = relationship(
        "TeamContest",
        back_populates="contest",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class TeamContest(Base, TimestampMixin):
    __tablename__ = "team_contests"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)

    team_id = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)

    contest_id = mapped_column(
        ForeignKey("contests.id", ondelete="CASCADE"), nullable=False
    )

    currency = mapped_column(Integer, default=1000, nullable=False)
    score = mapped_column(Integer, default=0, nullable=False)

    team = relationship("Team", back_populates="contests")
    contest = relationship("Contest", back_populates="teams")

    __table_args__ = (
        UniqueConstraint("team_id", "contest_id", name="uq_team_contest"),
        Index("ix_teamcontest_team_id", "team_id"),
        Index("ix_teamcontest_contest_id", "contest_id"),
    )
