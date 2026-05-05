"""Add content fields (input_format, output_format, constraints, sample_io) to builtin_problems

Revision ID: 0031
Revises: 0030
Create Date: 2026-05-05 00:00:00.000000+05:30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0031"
down_revision: Union[str, Sequence[str], None] = "0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("builtin_problems", sa.Column("input_format", sa.Text(), nullable=True))
    op.add_column("builtin_problems", sa.Column("output_format", sa.Text(), nullable=True))
    op.add_column("builtin_problems", sa.Column("constraints", sa.Text(), nullable=True))
    op.add_column(
        "builtin_problems",
        sa.Column(
            "sample_io",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("builtin_problems", "sample_io")
    op.drop_column("builtin_problems", "constraints")
    op.drop_column("builtin_problems", "output_format")
    op.drop_column("builtin_problems", "input_format")
