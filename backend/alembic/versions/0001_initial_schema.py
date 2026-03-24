"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-03-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # campaigns
    op.create_table('campaigns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('source_name', sa.String(100), nullable=True),
        sa.Column('source_url', sa.String(1000), nullable=True),
        sa.Column('promo_url', sa.String(1000), nullable=True),
        sa.Column('promo_type', sa.String(50), nullable=True),
        sa.Column('origin_program', sa.String(100), nullable=True),
        sa.Column('destination_program', sa.String(100), nullable=True),
        sa.Column('reference_month', sa.String(7), nullable=True),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_days', sa.Float(), nullable=True),
        sa.Column('is_flash', sa.Boolean(), nullable=True),
        sa.Column('bonus_pct_base', sa.Float(), nullable=True),
        sa.Column('bonus_pct_max', sa.Float(), nullable=True),
        sa.Column('min_transfer', sa.Integer(), nullable=True),
        sa.Column('max_transfer', sa.Integer(), nullable=True),
        sa.Column('max_bonus_miles', sa.Integer(), nullable=True),
        sa.Column('cpm_estimated', sa.Float(), nullable=True),
        sa.Column('cpm_min', sa.Float(), nullable=True),
        sa.Column('vpp_real_base', sa.Float(), nullable=True),
        sa.Column('vpp_real_clube', sa.Float(), nullable=True),
        sa.Column('vpp_real_elite', sa.Float(), nullable=True),
        sa.Column('stackable_with', sa.JSON(), nullable=True),
        sa.Column('not_stackable_with', sa.JSON(), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('extraction_method', sa.String(10), nullable=True),
        sa.Column('also_covered_by', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_campaigns_content_hash', 'campaigns', ['content_hash'], unique=True)
    op.create_index('ix_campaigns_destination_program', 'campaigns', ['destination_program'])
    op.create_index('ix_campaigns_origin_program', 'campaigns', ['origin_program'])
    op.create_index('ix_campaigns_promo_type', 'campaigns', ['promo_type'])
    op.create_index('ix_campaigns_reference_month', 'campaigns', ['reference_month'])
    op.create_index('ix_campaigns_source_name', 'campaigns', ['source_name'])

    # bonus_tiers
    op.create_table('bonus_tiers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), sa.ForeignKey('campaigns.id'), nullable=True),
        sa.Column('tier_name', sa.String(100), nullable=True),
        sa.Column('bonus_pct', sa.Float(), nullable=True),
        sa.Column('condition', sa.String(500), nullable=True),
        sa.Column('requires_club', sa.Boolean(), nullable=True),
        sa.Column('club_name', sa.String(100), nullable=True),
        sa.Column('requires_card', sa.Boolean(), nullable=True),
        sa.Column('card_name', sa.String(100), nullable=True),
        sa.Column('requires_category', sa.String(50), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_bonus_tiers_campaign_id', 'bonus_tiers', ['campaign_id'])

    # loyalty_duration_tiers
    op.create_table('loyalty_duration_tiers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), sa.ForeignKey('campaigns.id'), nullable=True),
        sa.Column('min_months', sa.Integer(), nullable=True),
        sa.Column('max_months', sa.Integer(), nullable=True),
        sa.Column('bonus_pct_extra', sa.Float(), nullable=True),
        sa.Column('label', sa.String(200), nullable=True),
        sa.Column('max_bonus_limit', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # scrape_runs
    op.create_table('scrape_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(100), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('campaigns_found', sa.Integer(), nullable=True),
        sa.Column('campaigns_new', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('is_bootstrap', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_scrape_runs_source_name', 'scrape_runs', ['source_name'])

    # alert_log
    op.create_table('alert_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), sa.ForeignKey('campaigns.id'), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('recipient_number', sa.String(20), nullable=True),
        sa.Column('message_preview', sa.String(200), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # bootstrap_state
    op.create_table('bootstrap_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(100), nullable=True),
        sa.Column('oldest_month_collected', sa.String(7), nullable=True),
        sa.Column('total_pages_scraped', sa.Integer(), nullable=True),
        sa.Column('total_campaigns_found', sa.Integer(), nullable=True),
        sa.Column('is_complete', sa.Boolean(), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_name')
    )


def downgrade() -> None:
    op.drop_table('bootstrap_state')
    op.drop_table('alert_log')
    op.drop_table('scrape_runs')
    op.drop_table('loyalty_duration_tiers')
    op.drop_table('bonus_tiers')
    op.drop_table('campaigns')
