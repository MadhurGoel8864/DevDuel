"""drop sample_io from builtin_problems and custom_problems

Revision ID: 0032
Revises: 0031
Create Date: 2026-05-06
"""

from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("builtin_problems", "sample_io")
    op.drop_column("custom_problems", "sample_io")


def downgrade() -> None:
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import JSONB

    op.add_column(
        "builtin_problems",
        sa.Column("sample_io", JSONB, nullable=True, server_default="[]"),
    )
    op.add_column(
        "custom_problems",
        sa.Column("sample_io", JSONB, nullable=False, server_default="[]"),
    )
