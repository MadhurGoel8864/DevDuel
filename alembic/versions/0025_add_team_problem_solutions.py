"""add_team_problem_solutions

Revision ID: 0025
Revises: 0024
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0025'
down_revision: Union[str, Sequence[str], None] = '0024'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'team_problem_solutions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('team_id', sa.String(length=36), nullable=False),
        sa.Column('contest_problem_id', sa.String(length=36), nullable=False),
        sa.Column('contest_id', sa.String(length=36), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=False),
        sa.Column('source_code', sa.Text(), nullable=False),
        sa.Column('last_submission_id', sa.String(length=36), nullable=True),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('Asia/Kolkata', now())"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contest_problem_id'], ['contest_problems.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contest_id'], ['contests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['last_submission_id'], ['submissions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'contest_problem_id', name='uq_tps_team_problem'),
    )
    op.create_index('ix_tps_contest_id', 'team_problem_solutions', ['contest_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_tps_contest_id', table_name='team_problem_solutions')
    op.drop_table('team_problem_solutions')
