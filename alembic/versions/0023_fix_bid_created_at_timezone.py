"""fix bid created_at timezone — use UTC instead of Asia/Kolkata

Revision ID: 0023
Revises: 0022
Create Date: 2026-04-10 13:37:00.000000+05:30

The Bid.created_at column was previously defaulting to Asia/Kolkata via
`func.timezone('Asia/Kolkata', func.now())`. The bidding service compares
timestamps in UTC, so this caused subtle drift where bids placed after the
auction deadline could pass validation. Standardize on UTC (`func.now()`).
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0023"
down_revision: Union[str, Sequence[str], None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Switch bids.created_at default from Asia/Kolkata to UTC."""
    op.alter_column(
        "bids",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Restore the prior Asia/Kolkata default."""
    op.alter_column(
        "bids",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text("timezone('Asia/Kolkata', now())"),
        existing_nullable=False,
    )
