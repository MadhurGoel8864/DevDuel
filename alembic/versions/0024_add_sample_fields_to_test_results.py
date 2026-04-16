"""add_sample_fields_to_test_results

Revision ID: 0024
Revises: 0023
Create Date: 2026-04-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0024'
down_revision: Union[str, Sequence[str], None] = '0023'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('submission_test_results', sa.Column('is_sample', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('submission_test_results', sa.Column('input', sa.Text(), nullable=True))
    op.add_column('submission_test_results', sa.Column('expected_output', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('submission_test_results', 'expected_output')
    op.drop_column('submission_test_results', 'input')
    op.drop_column('submission_test_results', 'is_sample')
