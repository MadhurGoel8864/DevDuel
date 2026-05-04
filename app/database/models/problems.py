"""BuiltinProblem, CustomProblem, and ContestProblem SQLAlchemy models."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column, relationship

from app.core.enums import Difficulty, ProblemKind
from app.database.models.base import Base
from app.database.utils import generate_uuid


class BuiltinProblem(Base):
    """Platform-curated coding problem available for contest creators to import."""

    __tablename__ = "builtin_problems"

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
    is_active = mapped_column(Boolean, default=True, nullable=False)

    # GCS URL pointing to the JSON file containing test cases for this problem
    test_cases_url = mapped_column(String(1024), nullable=True)

    created_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.timezone("Asia/Kolkata", func.now()),
        nullable=False,
    )
    updated_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.timezone("Asia/Kolkata", func.now()),
        onupdate=func.timezone("Asia/Kolkata", func.now()),
        nullable=False,
    )

    # Relationships
    contest_problems = relationship(
        "ContestProblem",
        back_populates="builtin_problem",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_builtin_problem_difficulty", "difficulty"),
        Index("ix_builtin_problem_slug", "slug", unique=True),
    )


class CustomProblem(Base):
    """Admin-authored coding problem owned by a single organizer.

    Reusable across multiple contests created by the same admin. Visible only
    to its owner; never to other organizers or to contestants except via
    a ContestProblem row inside a contest the contestant has joined.
    """

    __tablename__ = "custom_problems"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    created_by = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    title = mapped_column(String(255), nullable=False)
    # Slug is unique per-owner (see UniqueConstraint below), not globally.
    slug = mapped_column(String(300), nullable=False)

    description = mapped_column(Text, nullable=False)
    input_format = mapped_column(Text, nullable=False)
    output_format = mapped_column(Text, nullable=False)
    constraints = mapped_column(Text, nullable=False)
    sample_io = mapped_column(JSONB, nullable=False, server_default="[]")

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
    is_active = mapped_column(Boolean, default=True, nullable=False)

    test_cases_url = mapped_column(String(1024), nullable=True)

    created_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.timezone("Asia/Kolkata", func.now()),
        nullable=False,
    )
    updated_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.timezone("Asia/Kolkata", func.now()),
        onupdate=func.timezone("Asia/Kolkata", func.now()),
        nullable=False,
    )

    creator = relationship("User", lazy="selectin")
    contest_problems = relationship(
        "ContestProblem",
        back_populates="custom_problem",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index(
            "uq_custom_problem_owner_slug",
            "created_by",
            "slug",
            unique=True,
        ),
        Index("ix_custom_problem_created_by", "created_by"),
        Index("ix_custom_problem_difficulty", "difficulty"),
    )


class ContestProblem(Base):
    """Polymorphic join row linking a contest to either a BuiltinProblem or CustomProblem."""

    __tablename__ = "contest_problems"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)

    contest_id = mapped_column(
        String(36),
        ForeignKey("contests.id", ondelete="CASCADE"),
        nullable=False,
    )

    problem_kind = mapped_column(
        Enum(
            ProblemKind,
            name="problem_kind",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        nullable=False,
    )

    builtin_problem_id = mapped_column(
        String(36),
        ForeignKey("builtin_problems.id", ondelete="CASCADE"),
        nullable=True,
    )
    custom_problem_id = mapped_column(
        String(36),
        ForeignKey("custom_problems.id", ondelete="CASCADE"),
        nullable=True,
    )

    problem_order = mapped_column(Integer, nullable=False)

    # Contest-specific overrides (copied from underlying problem on import, editable by organizer)
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
    time_limit_ms = mapped_column(Integer, nullable=False)
    memory_limit_mb = mapped_column(Integer, nullable=False)

    is_active = mapped_column(Boolean, default=True, nullable=False)

    created_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.timezone("Asia/Kolkata", func.now()),
        nullable=False,
    )

    # Relationships
    contest = relationship("Contest", back_populates="problems", lazy="selectin")
    builtin_problem = relationship(
        "BuiltinProblem", back_populates="contest_problems", lazy="selectin"
    )
    custom_problem = relationship(
        "CustomProblem", back_populates="contest_problems", lazy="selectin"
    )

    @property
    def resolved_problem(self):
        """Return the underlying BuiltinProblem or CustomProblem regardless of kind.

        Both subtypes expose ``id``, ``title``, ``slug``, ``description``,
        ``test_cases_url``, ``points``, ``base_price``, ``time_limit_ms``,
        ``memory_limit_mb``, ``difficulty``, ``is_active``. Callers that only
        need those shared fields should prefer this property over manual dispatch.
        """
        return self.builtin_problem or self.custom_problem

    __table_args__ = (
        # Exactly one of (builtin_problem_id, custom_problem_id) must be set,
        # and it must agree with problem_kind.
        CheckConstraint(
            "(problem_kind = 'builtin' AND builtin_problem_id IS NOT NULL "
            "AND custom_problem_id IS NULL) "
            "OR (problem_kind = 'custom' AND custom_problem_id IS NOT NULL "
            "AND builtin_problem_id IS NULL)",
            name="ck_contest_problem_xor",
        ),
        # Per-kind partial unique indexes prevent the same problem being
        # imported into the same contest twice. We can't use a single
        # UniqueConstraint because each row only fills one of the two FKs.
        Index(
            "uq_contest_builtin_problem",
            "contest_id",
            "builtin_problem_id",
            unique=True,
            postgresql_where="builtin_problem_id IS NOT NULL",
        ),
        Index(
            "uq_contest_custom_problem",
            "contest_id",
            "custom_problem_id",
            unique=True,
            postgresql_where="custom_problem_id IS NOT NULL",
        ),
        Index("ix_contest_problem_contest_id", "contest_id"),
        Index("ix_contest_problem_builtin_problem_id", "builtin_problem_id"),
        Index("ix_contest_problem_custom_problem_id", "custom_problem_id"),
    )
