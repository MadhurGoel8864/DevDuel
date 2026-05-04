"""custom_problems table + polymorphic contest_problems

Revision ID: 0030
Revises: 0029
Create Date: 2026-05-04 00:00:00.000000+05:30

Manual migration to:
  1. Create 'problem_kind' enum type.
  2. Create 'custom_problems' table for admin-authored problems.
  3. Refactor 'contest_problems' to be polymorphic:
     - rename problem_id -> builtin_problem_id (nullable)
     - add custom_problem_id (nullable)
     - add problem_kind (NOT NULL, backfilled to 'builtin')
     - drop old uq_contest_problem unique constraint
     - add per-kind partial unique indexes
     - add CHECK constraint enforcing exactly one of (builtin_problem_id, custom_problem_id)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0030"
down_revision: Union[str, Sequence[str], None] = "0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create the problem_kind enum type
    problem_kind_enum = sa.Enum("builtin", "custom", name="problem_kind")
    problem_kind_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create custom_problems table
    op.create_table(
        "custom_problems",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("input_format", sa.Text(), nullable=False),
        sa.Column("output_format", sa.Text(), nullable=False),
        sa.Column("constraints", sa.Text(), nullable=False),
        sa.Column(
            "sample_io",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
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
        sa.Column("test_cases_url", sa.String(length=1024), nullable=True),
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
    )
    op.create_index(
        "uq_custom_problem_owner_slug",
        "custom_problems",
        ["created_by", "slug"],
        unique=True,
    )
    op.create_index(
        "ix_custom_problem_created_by",
        "custom_problems",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        "ix_custom_problem_difficulty",
        "custom_problems",
        ["difficulty"],
        unique=False,
    )

    # 3. Refactor contest_problems
    # 3a. Drop the existing unique constraint and index on problem_id (we'll
    #     replace with kind-aware partial unique indexes below).
    op.drop_constraint("uq_contest_problem", "contest_problems", type_="unique")
    op.drop_index("ix_contest_problem_problem_id", table_name="contest_problems")
    # 3b. Drop the FK so we can rename the column safely on Postgres.
    op.drop_constraint(
        "contest_problems_problem_id_fkey", "contest_problems", type_="foreignkey"
    )
    # 3c. Rename problem_id -> builtin_problem_id and make it nullable.
    op.alter_column(
        "contest_problems",
        "problem_id",
        new_column_name="builtin_problem_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )
    # 3d. Recreate the FK on the renamed column.
    op.create_foreign_key(
        "contest_problems_builtin_problem_id_fkey",
        "contest_problems",
        "builtin_problems",
        ["builtin_problem_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # 3e. Add custom_problem_id (nullable, FK to custom_problems).
    op.add_column(
        "contest_problems",
        sa.Column("custom_problem_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "contest_problems_custom_problem_id_fkey",
        "contest_problems",
        "custom_problems",
        ["custom_problem_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # 3f. Add problem_kind (nullable for now, backfill, then NOT NULL).
    op.add_column(
        "contest_problems",
        sa.Column(
            "problem_kind",
            postgresql.ENUM(
                "builtin", "custom", name="problem_kind", create_type=False
            ),
            nullable=True,
        ),
    )
    op.execute("UPDATE contest_problems SET problem_kind = 'builtin'")
    op.alter_column("contest_problems", "problem_kind", nullable=False)

    # 3g. Recreate the index on builtin_problem_id and add one for custom_problem_id.
    op.create_index(
        "ix_contest_problem_builtin_problem_id",
        "contest_problems",
        ["builtin_problem_id"],
        unique=False,
    )
    op.create_index(
        "ix_contest_problem_custom_problem_id",
        "contest_problems",
        ["custom_problem_id"],
        unique=False,
    )

    # 3h. Per-kind partial unique indexes (replaces the old uq_contest_problem).
    op.create_index(
        "uq_contest_builtin_problem",
        "contest_problems",
        ["contest_id", "builtin_problem_id"],
        unique=True,
        postgresql_where=sa.text("builtin_problem_id IS NOT NULL"),
    )
    op.create_index(
        "uq_contest_custom_problem",
        "contest_problems",
        ["contest_id", "custom_problem_id"],
        unique=True,
        postgresql_where=sa.text("custom_problem_id IS NOT NULL"),
    )

    # 3i. CHECK constraint: exactly one of the two FKs must be set, and it
    #     must agree with problem_kind.
    op.create_check_constraint(
        "ck_contest_problem_xor",
        "contest_problems",
        "(problem_kind = 'builtin' AND builtin_problem_id IS NOT NULL "
        "AND custom_problem_id IS NULL) "
        "OR (problem_kind = 'custom' AND custom_problem_id IS NOT NULL "
        "AND builtin_problem_id IS NULL)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse the contest_problems refactor.
    op.drop_constraint(
        "ck_contest_problem_xor", "contest_problems", type_="check"
    )
    op.drop_index("uq_contest_custom_problem", table_name="contest_problems")
    op.drop_index("uq_contest_builtin_problem", table_name="contest_problems")
    op.drop_index(
        "ix_contest_problem_custom_problem_id", table_name="contest_problems"
    )
    op.drop_index(
        "ix_contest_problem_builtin_problem_id", table_name="contest_problems"
    )

    op.drop_column("contest_problems", "problem_kind")

    op.drop_constraint(
        "contest_problems_custom_problem_id_fkey",
        "contest_problems",
        type_="foreignkey",
    )
    op.drop_column("contest_problems", "custom_problem_id")

    op.drop_constraint(
        "contest_problems_builtin_problem_id_fkey",
        "contest_problems",
        type_="foreignkey",
    )
    # Rename builtin_problem_id -> problem_id and restore NOT NULL.
    op.alter_column(
        "contest_problems",
        "builtin_problem_id",
        new_column_name="problem_id",
        existing_type=sa.String(length=36),
        nullable=False,
    )
    op.create_foreign_key(
        "contest_problems_problem_id_fkey",
        "contest_problems",
        "builtin_problems",
        ["problem_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_contest_problem_problem_id",
        "contest_problems",
        ["problem_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_contest_problem", "contest_problems", ["contest_id", "problem_id"]
    )

    # Drop custom_problems table.
    op.drop_index("ix_custom_problem_difficulty", table_name="custom_problems")
    op.drop_index("ix_custom_problem_created_by", table_name="custom_problems")
    op.drop_index("uq_custom_problem_owner_slug", table_name="custom_problems")
    op.drop_table("custom_problems")

    # Drop the problem_kind enum type.
    sa.Enum(name="problem_kind").drop(op.get_bind(), checkfirst=True)
