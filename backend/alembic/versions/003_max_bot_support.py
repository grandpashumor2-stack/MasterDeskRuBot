"""Add MAX messenger support: clients.max_id column and max_bot appointment source

Revision ID: 003_max_bot_support
Revises: 002_page_events
Create Date: 2026-07-17 23:30:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_max_bot_support'
down_revision: Union[str, None] = '002_page_events'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('clients', sa.Column('max_id', sa.String(length=50), nullable=True))
    op.create_index('ix_clients_max_id', 'clients', ['max_id'])
    op.execute("ALTER TYPE appointmentsource ADD VALUE IF NOT EXISTS 'max_bot'")


def downgrade() -> None:
    op.drop_index('ix_clients_max_id', table_name='clients')
    op.drop_column('clients', 'max_id')
    # Note: PostgreSQL does not support removing a value from an enum type.
    # Downgrading the 'max_bot' enum value requires recreating the type manually if ever needed.
