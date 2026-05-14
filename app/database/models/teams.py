from sqlalchemy import Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import mapped_column, relationship

from app.core.enums import JoinRequestStatus, TeamRole
from app.database.models.base import Base
from app.database.models.mixins import TimestampMixin
from app.database.utils import generate_uuid


class Team(Base, TimestampMixin):
    __tablename__ = "teams"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name = mapped_column(String(100), unique=True, nullable=False)

    created_by = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    creator = relationship("User")

    members = relationship(
        "TeamMember",
        back_populates="team",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    contests = relationship(
        "TeamContest",
        back_populates="team",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class TeamMember(Base, TimestampMixin):
    __tablename__ = "team_members"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)

    team_id = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)

    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    role = mapped_column(Enum(TeamRole), nullable=False)

    team = relationship("Team", back_populates="members")
    user = relationship("User", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_user"),
        Index("ix_teammember_team_id", "team_id"),
        Index("ix_teammember_user_id", "user_id"),
    )


class TeamJoinRequest(Base, TimestampMixin):
    """User-initiated request to join an existing team. Persisted with status."""

    __tablename__ = "team_join_requests"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)

    team_id = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )

    user_id = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    role = mapped_column(Enum(TeamRole), nullable=False)

    status = mapped_column(
        Enum(JoinRequestStatus),
        nullable=False,
        default=JoinRequestStatus.PENDING,
    )

    team = relationship("Team")
    user = relationship("User")

    __table_args__ = (
        Index("ix_team_join_requests_team_id", "team_id"),
        Index("ix_team_join_requests_user_id", "user_id"),
        Index("ix_team_join_requests_status", "status"),
    )
