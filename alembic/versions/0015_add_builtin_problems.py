"""Add builtin_problems table

Revision ID: 0015
Revises: 0014
Create Date: 2026-03-18 01:07:00.000000+05:30

Manual migration to:
  1. Create 'builtin_problems' table (platform-curated, no user FK).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0015"
down_revision: Union[str, Sequence[str], None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "builtin_problems",
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_builtin_problem_slug"),
    )
    op.create_index(
        "ix_builtin_problem_difficulty",
        "builtin_problems",
        ["difficulty"],
        unique=False,
    )
    op.create_index(
        "ix_builtin_problem_slug", "builtin_problems", ["slug"], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_builtin_problem_slug", table_name="builtin_problems")
    op.drop_index("ix_builtin_problem_difficulty", table_name="builtin_problems")
    op.drop_table("builtin_problems")
