"""add_is_organizer_to_users

Revision ID: 0018
Revises: 0017
Create Date: 2026-03-23 00:00:00.000000+05:30

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0018"
down_revision: Union[str, Sequence[str], None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_organizer boolean column to users table (default False)."""
    op.add_column(
        "users",
        sa.Column("is_organizer", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Remove is_organizer column from users table."""
    op.drop_column("users", "is_organizer")
