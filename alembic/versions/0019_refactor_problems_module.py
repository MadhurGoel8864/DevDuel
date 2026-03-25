"""refactor_problems_module

Revision ID: 0019
Revises: 0018
Create Date: 2026-03-25 00:43:21.037473+05:30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0019'
down_revision: Union[str, Sequence[str], None] = '0018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    1. Add override columns to contest_problems (nullable first).
    2. Populate them from the joined problems table.
    3. Change FK from problems.id to builtin_problems.id.
    4. Set columns NOT NULL.
    5. Drop the problems table.
    6. Drop the unique constraint on (contest_id, problem_order).
    """
    # Step 1: Add columns as nullable
    op.add_column('contest_problems', sa.Column('difficulty', sa.Enum('easy', 'medium', 'hard', name='difficulty'), nullable=True))
    op.add_column('contest_problems', sa.Column('points', sa.Integer(), nullable=True))
    op.add_column('contest_problems', sa.Column('base_price', sa.Integer(), nullable=True))
    op.add_column('contest_problems', sa.Column('time_limit_ms', sa.Integer(), nullable=True))
    op.add_column('contest_problems', sa.Column('memory_limit_mb', sa.Integer(), nullable=True))

    # Step 2: Populate from joined problems table (for any existing rows)
    op.execute("""
        UPDATE contest_problems cp
        SET difficulty = p.difficulty,
            points = p.points,
            base_price = p.base_price,
            time_limit_ms = p.time_limit_ms,
            memory_limit_mb = p.memory_limit_mb
        FROM problems p
        WHERE cp.problem_id = p.id
    """)

    # Set defaults for any rows that didn't join (shouldn't happen, but safety)
    op.execute("""
        UPDATE contest_problems
        SET difficulty = 'easy',
            points = COALESCE(points, 100),
            base_price = COALESCE(base_price, 50),
            time_limit_ms = COALESCE(time_limit_ms, 2000),
            memory_limit_mb = COALESCE(memory_limit_mb, 256)
        WHERE difficulty IS NULL
    """)

    # Step 3: Set columns NOT NULL
    op.alter_column('contest_problems', 'difficulty', nullable=False)
    op.alter_column('contest_problems', 'points', nullable=False)
    op.alter_column('contest_problems', 'base_price', nullable=False)
    op.alter_column('contest_problems', 'time_limit_ms', nullable=False)
    op.alter_column('contest_problems', 'memory_limit_mb', nullable=False)

    # Step 4: Drop unique constraint on (contest_id, problem_order)
    op.drop_constraint('uq_contest_problem_order', 'contest_problems', type_='unique')

    # Step 5: Change FK from problems to builtin_problems
    op.drop_constraint('contest_problems_problem_id_fkey', 'contest_problems', type_='foreignkey')

    # Clear existing contest_problems data since problem_ids reference problems table,
    # not builtin_problems. Existing data is dev/test only.
    op.execute("DELETE FROM contest_problems")

    op.create_foreign_key(
        'contest_problems_problem_id_fkey',
        'contest_problems', 'builtin_problems',
        ['problem_id'], ['id'],
        ondelete='CASCADE'
    )

    # Step 6: Drop the problems table
    op.drop_index('ix_problem_difficulty', table_name='problems')
    op.drop_index('ix_problem_slug', table_name='problems')
    op.drop_table('problems')


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate problems table
    op.create_table('problems',
        sa.Column('id', sa.VARCHAR(length=36), autoincrement=False, nullable=False),
        sa.Column('title', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
        sa.Column('slug', sa.VARCHAR(length=300), autoincrement=False, nullable=False),
        sa.Column('description', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('difficulty', postgresql.ENUM('easy', 'medium', 'hard', name='difficulty'), autoincrement=False, nullable=False),
        sa.Column('points', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('base_price', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('time_limit_ms', sa.INTEGER(), server_default=sa.text('2000'), autoincrement=False, nullable=False),
        sa.Column('memory_limit_mb', sa.INTEGER(), server_default=sa.text('256'), autoincrement=False, nullable=False),
        sa.Column('created_by', sa.VARCHAR(length=36), autoincrement=False, nullable=False),
        sa.Column('is_active', sa.BOOLEAN(), server_default=sa.text('true'), autoincrement=False, nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text("timezone('Asia/Kolkata'::text, now())"), autoincrement=False, nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text("timezone('Asia/Kolkata'::text, now())"), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='problems_created_by_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='problems_pkey'),
        sa.UniqueConstraint('slug', name='uq_problem_slug')
    )
    op.create_index('ix_problem_slug', 'problems', ['slug'], unique=True)
    op.create_index('ix_problem_difficulty', 'problems', ['difficulty'], unique=False)

    # Revert FK
    op.drop_constraint('contest_problems_problem_id_fkey', 'contest_problems', type_='foreignkey')
    op.create_foreign_key('contest_problems_problem_id_fkey', 'contest_problems', 'problems', ['problem_id'], ['id'], ondelete='CASCADE')

    # Restore unique constraint
    op.create_unique_constraint('uq_contest_problem_order', 'contest_problems', ['contest_id', 'problem_order'])

    # Drop override columns
    op.drop_column('contest_problems', 'memory_limit_mb')
    op.drop_column('contest_problems', 'time_limit_ms')
    op.drop_column('contest_problems', 'base_price')
    op.drop_column('contest_problems', 'points')
    op.drop_column('contest_problems', 'difficulty')
