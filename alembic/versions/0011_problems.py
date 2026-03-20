"""Create problems and contest_problems tables

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-05 22:08:28.000000+05:30

Manual migration to:
  1. Create 'difficulty' enum type.
  2. Create 'problems' table.
  3. Create 'contest_problems' table.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: Union[str, Sequence[str], None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create 'difficulty' enum type
    difficulty_enum = sa.Enum("easy", "medium", "hard", name="difficulty")
    difficulty_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create 'problems' table
    op.create_table(
        "problems",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "difficulty",
            postgresql.ENUM(
                "easy", "medium", "hard", name="difficulty", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("base_price", sa.Integer(), nullable=False),
        sa.Column("time_limit_ms", sa.Integer(), nullable=False, server_default="2000"),
        sa.Column(
            "memory_limit_mb", sa.Integer(), nullable=False, server_default="256"
        ),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('Asia/Kolkata', now())"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('Asia/Kolkata', now())"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_problem_slug"),
    )
    op.create_index("ix_problem_difficulty", "problems", ["difficulty"], unique=False)
    op.create_index("ix_problem_slug", "problems", ["slug"], unique=True)

    # 3. Create 'contest_problems' table
    op.create_table(
        "contest_problems",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("contest_id", sa.String(length=36), nullable=False),
        sa.Column("problem_id", sa.String(length=36), nullable=False),
        sa.Column("problem_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('Asia/Kolkata', now())"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["contest_id"], ["contests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contest_id", "problem_id", name="uq_contest_problem"),
        sa.UniqueConstraint(
            "contest_id", "problem_order", name="uq_contest_problem_order"
        ),
    )
    op.create_index(
        "ix_contest_problem_contest_id",
        "contest_problems",
        ["contest_id"],
        unique=False,
    )
    op.create_index(
        "ix_contest_problem_problem_id",
        "contest_problems",
        ["problem_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_contest_problem_problem_id", table_name="contest_problems")
    op.drop_index("ix_contest_problem_contest_id", table_name="contest_problems")
    op.drop_table("contest_problems")

    op.drop_index("ix_problem_slug", table_name="problems")
    op.drop_index("ix_problem_difficulty", table_name="problems")
    op.drop_table("problems")

    sa.Enum(name="difficulty").drop(op.get_bind(), checkfirst=True)
