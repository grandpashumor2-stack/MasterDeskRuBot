"""Add companies.max_chat_id for owner notifications via MAX messenger

Revision ID: 004_company_max_chat_id
Revises: 003_max_bot_support
Create Date: 2026-07-18 09:30:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004_company_max_chat_id'
down_revision: Union[str, None] = '003_max_bot_support'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('companies', sa.Column('max_chat_id', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'max_chat_id')
