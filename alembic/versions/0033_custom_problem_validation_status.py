"""add validation_status and validated_at to custom_problems

Revision ID: 0033
Revises: 0032
Create Date: 2026-05-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE validation_status AS ENUM ('UNVALIDATED', 'VALID', 'INVALID')")
    op.add_column(
        "custom_problems",
        sa.Column(
            "validation_status",
            sa.Enum("UNVALIDATED", "VALID", "INVALID", name="validation_status"),
            nullable=False,
            server_default="UNVALIDATED",
        ),
    )
    op.add_column(
        "custom_problems",
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("custom_problems", "validated_at")
    op.drop_column("custom_problems", "validation_status")
    op.execute("DROP TYPE validation_status")
