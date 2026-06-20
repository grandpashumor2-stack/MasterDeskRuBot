from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from datetime import datetime, timedelta
from uuid import UUID

from app.infrastructure.database.connection import get_db
from app.core.security import get_current_owner, get_current_admin
from app.domain.models.appointment import Appointment, AppointmentStatus
from app.domain.models.client import Client
from app.domain.models.message import Message
from app.domain.models.service import Service
from app.domain.models.subscription import Subscription, SubscriptionStatus

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/company/{company_id}/dashboard")
async def company_dashboard(
    company_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Today appointments
    today_apts = await session.execute(
        select(func.count()).where(and_(
            Appointment.company_id == company_id,
            Appointment.scheduled_at >= today_start,
        ))
    )
    
    # Month appointments
    month_apts = await session.execute(
        select(func.count()).where(and_(
            Appointment.company_id == company_id,
            Appointment.created_at >= month_start,
        ))
    )
    
    # Total clients
    total_clients = await session.execute(
        select(func.count()).where(Client.company_id == company_id)
    )
    
    # Returning clients
    returning = await session.execute(
        select(func.count()).where(and_(
            Client.company_id == company_id,
            Client.visit_count >= 2,
        ))
    )
    
    # Total messages
    total_msgs = await session.execute(
        select(func.count()).where(Message.company_id == company_id)
    )
    
    # Top services
    top_services_result = await session.execute(
        select(Service.name, func.count(Appointment.id).label("count"))
        .join(Appointment, Appointment.service_id == Service.id, isouter=True)
        .where(Service.company_id == company_id)
        .group_by(Service.name)
        .order_by(desc("count"))
        .limit(5)
    )
    top_services = [{"name": row[0], "count": row[1]} for row in top_services_result]
    
    # Conversion rate (messages → appointments)
    msg_count = total_msgs.scalar()
    apt_count = month_apts.scalar()
    conversion = round(apt_count / msg_count * 100, 1) if msg_count > 0 else 0
    
    return {
        "today_appointments": today_apts.scalar(),
        "month_appointments": apt_count,
        "total_clients": total_clients.scalar(),
        "returning_clients": returning.scalar(),
        "total_messages": msg_count,
        "conversion_rate": conversion,
        "top_services": top_services,
    }


@router.get("/admin/platform")
async def platform_stats(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Platform-wide stats for admin."""
    # Total companies
    from app.domain.models.company import Company
    total_companies = await session.execute(select(func.count()).select_from(Company))
    
    # Active subscriptions
    active_subs = await session.execute(
        select(func.count()).where(Subscription.status == SubscriptionStatus.ACTIVE)
    )
    
    # Trial subscriptions
    trial_subs = await session.execute(
        select(func.count()).where(Subscription.status == SubscriptionStatus.TRIAL)
    )
    
    # MRR calculation
    from app.domain.repositories.subscription import SubscriptionRepository
    sub_repo = SubscriptionRepository(session)
    mrr = await sub_repo.get_mrr()
    
    # Churn: cancelled in last 30 days
    month_ago = datetime.utcnow() - timedelta(days=30)
    churned = await session.execute(
        select(func.count()).where(and_(
            Subscription.status == SubscriptionStatus.CANCELLED,
            Subscription.updated_at >= month_ago,
        ))
    )
    
    return {
        "total_companies": total_companies.scalar(),
        "active_subscriptions": active_subs.scalar(),
        "trial_subscriptions": trial_subs.scalar(),
        "mrr": round(mrr, 2),
        "arr": round(mrr * 12, 2),
        "churned_last_30_days": churned.scalar(),
    }
