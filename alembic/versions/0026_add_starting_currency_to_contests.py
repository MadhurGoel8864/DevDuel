"""add_starting_currency_to_contests

Revision ID: 0026
Revises: 0025
Create Date: 2026-04-17 23:30:00.000000+05:30

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0026"
down_revision: Union[str, Sequence[str], None] = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "contests",
        sa.Column(
            "starting_currency",
            sa.Integer(),
            nullable=False,
            server_default="1000",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("contests", "starting_currency")
