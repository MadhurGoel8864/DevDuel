"""Submission-related SQLAlchemy models: Submission, SubmissionTestResult, TeamProblemSolution."""

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

from app.core.enums import SubmissionVerdict
from app.database.models.base import Base
from app.database.utils import generate_uuid


class Submission(Base):
    """A code submission by a team for a contest problem."""

    __tablename__ = "submissions"

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
    assignment_id = mapped_column(
        String(36),
        ForeignKey("contest_problem_assignments.id", ondelete="CASCADE"),
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
        nullable=True,
    )

    # Code
    language = mapped_column(String(50), nullable=False)
    language_id = mapped_column(Integer, nullable=False)
    source_code = mapped_column(Text, nullable=False)

    # Verdict
    verdict = mapped_column(
        Enum(SubmissionVerdict, name="submissionverdict"),
        default=SubmissionVerdict.PENDING,
        nullable=False,
    )
    passed_test_cases = mapped_column(Integer, default=0)
    total_test_cases = mapped_column(Integer, default=0)

    # Performance (worst case across all test cases)
    max_time_ms = mapped_column(Integer, nullable=True)
    max_memory_kb = mapped_column(Integer, nullable=True)

    # Judge0 tracking
    judge0_tokens = mapped_column(Text, nullable=True)  # comma-separated tokens

    # Error output (first failing test case)
    compile_output = mapped_column(Text, nullable=True)
    stderr = mapped_column(Text, nullable=True)
    error_message = mapped_column(Text, nullable=True)

    # Timestamps
    submitted_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.timezone("Asia/Kolkata", func.now()),
        nullable=False,
    )
    judged_at = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    test_results = relationship(
        "SubmissionTestResult",
        back_populates="submission",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_submission_contest_id", "contest_id"),
        Index("ix_submission_team_id", "team_id"),
        Index("ix_submission_assignment_id", "assignment_id"),
    )


class SubmissionTestResult(Base):
    """Result of running a submission against a single test case."""

    __tablename__ = "submission_test_results"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)

    submission_id = mapped_column(
        String(36),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    test_case_index = mapped_column(Integer, nullable=False)  # 0-based order

    judge0_token = mapped_column(String(100), nullable=True)
    status_id = mapped_column(Integer, nullable=False)  # Judge0 status ID
    verdict = mapped_column(String(50), nullable=False)  # "ACCEPTED", "WRONG_ANSWER", etc.

    stdout = mapped_column(Text, nullable=True)
    stderr = mapped_column(Text, nullable=True)
    compile_output = mapped_column(Text, nullable=True)

    time_ms = mapped_column(Integer, nullable=True)
    memory_kb = mapped_column(Integer, nullable=True)

    # Sample test case fields (only populated when is_sample=True)
    is_sample = mapped_column(Boolean, nullable=False, default=False)
    input = mapped_column(Text, nullable=True)
    expected_output = mapped_column(Text, nullable=True)

    # Relationships
    submission = relationship("Submission", back_populates="test_results")

    __table_args__ = (
        Index("ix_str_submission_id", "submission_id"),
    )


class TeamProblemSolution(Base):
    """The latest submitted code by a team for a contest problem.

    Upserted on every submission so editor rehydration, organizer review,
    and submission history can all read the most recent code with O(1) lookup.
    The full per-submission audit trail still lives on `submissions`.
    """

    __tablename__ = "team_problem_solutions"

    id = mapped_column(String(36), primary_key=True, default=generate_uuid)

    team_id = mapped_column(
        String(36),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    contest_problem_id = mapped_column(
        String(36),
        ForeignKey("contest_problems.id", ondelete="CASCADE"),
        nullable=False,
    )
    contest_id = mapped_column(
        String(36),
        ForeignKey("contests.id", ondelete="CASCADE"),
        nullable=False,
    )

    language = mapped_column(String(50), nullable=False)
    source_code = mapped_column(Text, nullable=False)

    last_submission_id = mapped_column(
        String(36),
        ForeignKey("submissions.id", ondelete="SET NULL"),
        nullable=True,
    )

    updated_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.timezone("Asia/Kolkata", func.now()),
        onupdate=func.timezone("Asia/Kolkata", func.now()),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "team_id", "contest_problem_id", name="uq_tps_team_problem"
        ),
        Index("ix_tps_contest_id", "contest_id"),
    )
