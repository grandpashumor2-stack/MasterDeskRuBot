"""Initial migration — all tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PLANS
    op.create_table('plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.Enum('start','business','premium', name='planname'), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('monthly_price', sa.Numeric(10,2), nullable=False),
        sa.Column('yearly_price', sa.Numeric(10,2), nullable=False),
        sa.Column('limits', postgresql.JSONB(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # COMPANIES
    op.create_table('companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('telegram_bot_token', sa.String(100)),
        sa.Column('telegram_chat_id', sa.String(50)),
        sa.Column('phone', sa.String(20)),
        sa.Column('address', sa.String(500)),
        sa.Column('city', sa.String(100)),
        sa.Column('description', sa.Text()),
        sa.Column('logo_url', sa.String(500)),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('ai_system_prompt', sa.Text()),
        sa.Column('settings', postgresql.JSONB(), default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        sa.UniqueConstraint('telegram_bot_token'),
    )

    # WORKING_HOURS
    op.create_table('working_hours',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('is_working', sa.Boolean(), default=True),
        sa.Column('open_time', sa.Time()),
        sa.Column('close_time', sa.Time()),
        sa.Column('break_start', sa.Time()),
        sa.Column('break_end', sa.Time()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'day_of_week'),
    )

    # USERS
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('role', sa.Enum('platform_admin','company_owner','employee', name='role'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True)),
        sa.Column('telegram_id', sa.String(50)),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('telegram_id'),
    )

    # EMPLOYEES
    op.create_table('employees',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20)),
        sa.Column('specialization', sa.String(255)),
        sa.Column('telegram_id', sa.String(50)),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('schedule', postgresql.JSONB(), default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # CLIENTS
    op.create_table('clients',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('telegram_id', sa.String(50)),
        sa.Column('telegram_username', sa.String(100)),
        sa.Column('full_name', sa.String(255)),
        sa.Column('phone', sa.String(20)),
        sa.Column('notes', sa.String(1000)),
        sa.Column('visit_count', sa.Integer(), default=0),
        sa.Column('last_visit_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # VEHICLES
    op.create_table('vehicles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('make', sa.String(100)),
        sa.Column('model', sa.String(100)),
        sa.Column('year', sa.Integer()),
        sa.Column('license_plate', sa.String(20)),
        sa.Column('vin', sa.String(17)),
        sa.Column('mileage', sa.Integer()),
        sa.Column('extra', postgresql.JSONB(), default=dict),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # SERVICES
    op.create_table('services',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('category', sa.Enum('maintenance','diagnostics','engine','transmission',
                   'suspension','brakes','electrical','body','tires','ac','other', name='servicecategory')),
        sa.Column('duration_minutes', sa.Integer(), default=60),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('keywords', postgresql.JSONB(), default=list),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # SERVICE_PRICES
    op.create_table('service_prices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('price_type', sa.Enum('fixed','range','by_make','on_request', name='pricetype')),
        sa.Column('fixed_price', sa.Numeric(10,2)),
        sa.Column('price_min', sa.Numeric(10,2)),
        sa.Column('price_max', sa.Numeric(10,2)),
        sa.Column('prices_by_make', postgresql.JSONB(), default=dict),
        sa.Column('car_make', sa.String(100)),
        sa.Column('is_default', sa.Boolean(), default=False),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # APPOINTMENTS
    op.create_table('appointments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True)),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True)),
        sa.Column('service_id', postgresql.UUID(as_uuid=True)),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True)),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), default=60),
        sa.Column('status', sa.Enum('pending','confirmed','in_progress','completed','cancelled','no_show', name='appointmentstatus'), default='pending'),
        sa.Column('source', sa.Enum('telegram_bot','web_panel','phone','walk_in', name='appointmentsource'), default='telegram_bot'),
        sa.Column('client_phone', sa.String(20)),
        sa.Column('client_name', sa.String(255)),
        sa.Column('car_description', sa.String(500)),
        sa.Column('problem_description', sa.Text()),
        sa.Column('notes', sa.Text()),
        sa.Column('reminder_24h_sent', sa.Boolean(), default=False),
        sa.Column('reminder_2h_sent', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_appointments_company_scheduled', 'appointments', ['company_id', 'scheduled_at'])
    op.create_index('ix_appointments_status', 'appointments', ['status'])

    # MESSAGES
    op.create_table('messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True)),
        sa.Column('telegram_id', sa.String(50)),
        sa.Column('direction', sa.Enum('incoming','outgoing', name='messagedirection')),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('is_ai_response', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_messages_company_telegram', 'messages', ['company_id', 'telegram_id'])

    # CAMPAIGNS
    op.create_table('campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('draft','scheduled','sending','sent','cancelled', name='campaignstatus'), default='draft'),
        sa.Column('segment_filter', postgresql.JSONB(), default=dict),
        sa.Column('scheduled_at', sa.DateTime()),
        sa.Column('sent_at', sa.DateTime()),
        sa.Column('sent_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ANALYTICS
    op.create_table('analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.Enum('message_received','appointment_created','appointment_completed',
                   'appointment_cancelled','client_returned','campaign_sent','price_requested', name='eventtype')),
        sa.Column('data', postgresql.JSONB(), default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # SUBSCRIPTIONS
    op.create_table('subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.Enum('trial','active','past_due','cancelled','expired', name='subscriptionstatus'), default='trial'),
        sa.Column('is_yearly', sa.Boolean(), default=False),
        sa.Column('trial_ends_at', sa.DateTime()),
        sa.Column('current_period_start', sa.DateTime()),
        sa.Column('current_period_end', sa.DateTime()),
        sa.Column('dialogs_used', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id'),
    )

    # PAYMENTS
    op.create_table('payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(10,2), nullable=False),
        sa.Column('status', sa.Enum('pending','paid','failed','refunded', name='paymentstatus'), default='pending'),
        sa.Column('payment_method', sa.String(100)),
        sa.Column('external_id', sa.String(255)),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # INVOICES
    op.create_table('invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('number', sa.String(50), nullable=False),
        sa.Column('amount', sa.Numeric(10,2), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('is_paid', sa.Boolean(), default=False),
        sa.Column('paid_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('number'),
    )


def downgrade() -> None:
    op.drop_table('invoices')
    op.drop_table('payments')
    op.drop_table('subscriptions')
    op.drop_table('analytics')
    op.drop_table('campaigns')
    op.drop_table('messages')
    op.drop_table('appointments')
    op.drop_table('service_prices')
    op.drop_table('services')
    op.drop_table('vehicles')
    op.drop_table('clients')
    op.drop_table('employees')
    op.drop_table('users')
    op.drop_table('working_hours')
    op.drop_table('companies')
    op.drop_table('plans')
    for enum in ['planname','role','servicecategory','pricetype','appointmentstatus',
                 'appointmentsource','messagedirection','campaignstatus','eventtype',
                 'subscriptionstatus','paymentstatus']:
        op.execute(f'DROP TYPE IF EXISTS {enum}')
