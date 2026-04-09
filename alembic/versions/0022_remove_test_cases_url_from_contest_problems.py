"""remove_test_cases_url_from_contest_problems

Revision ID: 0022
Revises: 0021
Create Date: 2026-04-09 22:50:00.000000+05:30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0022'
down_revision: Union[str, Sequence[str], None] = '0021'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove test_cases_url from contest_problems — test cases belong to builtin_problems only."""
    op.drop_column('contest_problems', 'test_cases_url')


def downgrade() -> None:
    """Re-add test_cases_url to contest_problems."""
    op.add_column('contest_problems', sa.Column('test_cases_url', sa.String(length=1024), nullable=True))
