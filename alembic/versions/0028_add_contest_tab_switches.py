"""add_contest_tab_switches

Revision ID: 0028
Revises: 0027
Create Date: 2026-04-20

Tracks how many times each participant switches away from the contest tab.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0028"
down_revision: Union[str, None] = "0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contest_tab_switches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "contest_id",
            sa.String(36),
            sa.ForeignKey("contests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            sa.String(36),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("switch_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_switched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "contest_id", "user_id", name="uq_contest_tab_switch_contest_user"
        ),
    )
    op.create_index(
        "ix_contest_tab_switches_contest_id",
        "contest_tab_switches",
        ["contest_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_contest_tab_switches_contest_id", table_name="contest_tab_switches"
    )
    op.drop_table("contest_tab_switches")
