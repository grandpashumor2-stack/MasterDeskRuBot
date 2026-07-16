"""Add page_events table for marketing funnel tracking

Revision ID: 002_page_events
Revises: 001_initial
Create Date: 2026-07-13 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '002_page_events'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('page_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('referral_code', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_page_events_event_type', 'page_events', ['event_type'])
    op.create_index('ix_page_events_created_at', 'page_events', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_page_events_created_at', table_name='page_events')
    op.drop_index('ix_page_events_event_type', table_name='page_events')
    op.drop_table('page_events')
