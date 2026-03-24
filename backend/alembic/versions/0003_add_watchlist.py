"""add watchlist_entries table

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-24

"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('watchlist_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phone_number', sa.String(20), nullable=False),
        sa.Column('destination_program', sa.String(100), nullable=True),
        sa.Column('origin_program', sa.String(100), nullable=True),
        sa.Column('min_bonus_pct', sa.Float(), nullable=True, server_default='40.0'),
        sa.Column('max_cpm', sa.Float(), nullable=True, server_default='20.0'),
        sa.Column('flash_only', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_alerted_at', sa.DateTime(), nullable=True),
        sa.Column('alert_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('label', sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_watchlist_phone', 'watchlist_entries', ['phone_number'])
    op.create_index('ix_watchlist_active', 'watchlist_entries', ['active'])


def downgrade() -> None:
    op.drop_table('watchlist_entries')
