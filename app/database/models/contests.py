from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import mapped_column, relationship
from datetime import datetime

from app.core.enums import ContestStatus
from app.database.models.base import Base
from app.database.models.mixins import TimestampMixin
from app.database.utils import generate_uuid


class Contest(Base, TimestampMixin):
    __tablename__ = "contests"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name = mapped_column(String(100), nullable=False)
    description = mapped_column(String(1000), nullable=True)

    start_time = mapped_column(DateTime(timezone=True), nullable=False)
    end_time = mapped_column(DateTime(timezone=True), nullable=False)

    created_by = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    status = mapped_column(
        Enum(ContestStatus, name="conteststatus"),
        default=ContestStatus.DRAFT,
        nullable=False,
    )

    starting_currency = mapped_column(Integer, default=1000, nullable=False)

    teams = relationship(
        "TeamContest",
        back_populates="contest",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    problems = relationship(
        "ContestProblem",
        back_populates="contest",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ContestProblem.problem_order",
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

    # True  = team is actively competing
    # False = a member left mid-contest, team is frozen
    #         record preserved for history
    is_active = mapped_column(Boolean, default=True, nullable=False)

    team = relationship("Team", back_populates="contests")
    contest = relationship("Contest", back_populates="teams")

    __table_args__ = (
        UniqueConstraint("team_id", "contest_id", name="uq_team_contest"),
        Index("ix_teamcontest_team_id", "team_id"),
        Index("ix_teamcontest_contest_id", "contest_id"),
    )


class ContestTabSwitch(Base, TimestampMixin):
    __tablename__ = "contest_tab_switches"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    contest_id = mapped_column(ForeignKey("contests.id", ondelete="CASCADE"), nullable=False)
    team_id = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    switch_count = mapped_column(Integer, default=0, nullable=False)
    last_switched_at = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("contest_id", "user_id", name="uq_contest_tab_switch_contest_user"),
        Index("ix_contest_tab_switches_contest_id", "contest_id"),
    )
