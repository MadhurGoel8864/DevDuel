"""configure_ist_timezone

Revision ID: 0003
Revises: 0002
Create Date: 2025-12-30 14:13:37.503009+05:30

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Set the database session timezone to IST
    op.execute("SET TIME ZONE 'Asia/Kolkata';")

    # Note: The TimestampMixin changes will automatically apply to new records
    # Existing records already have timezone-aware timestamps and will be
    # converted to IST by the application layer when retrieved
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # Revert timezone to UTC
    op.execute("SET TIME ZONE 'UTC';")
    pass
    # ### end Alembic commands ###
