"""add_team_join_requests

Revision ID: 0027
Revises: 0026
Create Date: 2026-04-20 09:22:00.000000+05:30

Creates the team_join_requests table and the joinrequeststatus enum.
The teamrole enum already exists (from migration 0008) so we reference it
without re-creating.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0027"
down_revision: Union[str, Sequence[str], None] = "0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Existing enum — referenced by name only, never created here.
teamrole_enum = postgresql.ENUM(
    "BIDDING", "CODING", name="teamrole", create_type=False
)

# New enum — must be created explicitly before the table.
joinrequeststatus_enum = postgresql.ENUM(
    "PENDING",
    "ACCEPTED",
    "REJECTED",
    "CANCELLED",
    name="joinrequeststatus",
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    joinrequeststatus_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "team_join_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("team_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role", teamrole_enum, nullable=False),
        sa.Column(
            "status",
            joinrequeststatus_enum,
            nullable=False,
            server_default="PENDING",
        ),
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
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_team_join_requests_team_id",
        "team_join_requests",
        ["team_id"],
        unique=False,
    )
    op.create_index(
        "ix_team_join_requests_user_id",
        "team_join_requests",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_team_join_requests_status",
        "team_join_requests",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_team_join_requests_status", table_name="team_join_requests")
    op.drop_index("ix_team_join_requests_user_id", table_name="team_join_requests")
    op.drop_index("ix_team_join_requests_team_id", table_name="team_join_requests")
    op.drop_table("team_join_requests")
    joinrequeststatus_enum.drop(op.get_bind(), checkfirst=True)
