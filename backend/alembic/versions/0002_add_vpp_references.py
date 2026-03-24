"""add vpp_references table

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-22

"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('vpp_references',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('program', sa.String(100), nullable=True),
        sa.Column('reference_date', sa.DateTime(), nullable=True),
        sa.Column('vpp_perceived', sa.Float(), nullable=True),
        sa.Column('source_blog', sa.String(100), nullable=True),
        sa.Column('source_url', sa.String(1000), nullable=True),
        sa.Column('raw_excerpt', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_vpp_references_program', 'vpp_references', ['program'])
    op.create_index('ix_vpp_references_reference_date', 'vpp_references', ['reference_date'])


def downgrade() -> None:
    op.drop_table('vpp_references')
