"""add allowed_email_domain to contests

Revision ID: 0029
Revises: 0028
Create Date: 2026-04-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0029"
down_revision: Union[str, None] = "0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "contests",
        sa.Column("allowed_email_domain", sa.String(253), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("contests", "allowed_email_domain")
