from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from decimal import Decimal
from uuid import UUID

from app.infrastructure.database.connection import get_db
from app.core.security import get_current_admin
from app.domain.models.company import Company
from app.domain.models.subscription import Plan, Subscription, SubscriptionStatus, PlanName
from app.domain.repositories.subscription import PlanRepository, SubscriptionRepository
from app.domain.repositories.company import CompanyRepository

router = APIRouter(prefix="/admin", tags=["admin"])


class PlanUpdate(BaseModel):
    monthly_price: Decimal | None = None
    yearly_price: Decimal | None = None
    limits: dict | None = None
    is_active: bool | None = None


@router.get("/companies")
async def list_companies(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    result = await session.execute(select(Company).order_by(Company.created_at.desc()))
    return list(result.scalars().all())


@router.get("/plans")
async def list_plans(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    repo = PlanRepository(session)
    return await repo.get_active_plans()


@router.patch("/plans/{plan_id}")
async def update_plan(
    plan_id: UUID,
    data: PlanUpdate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Update plan pricing and limits without code changes."""
    plan = await session.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    if data.monthly_price is not None:
        plan.monthly_price = data.monthly_price
    if data.yearly_price is not None:
        plan.yearly_price = data.yearly_price
    if data.limits is not None:
        plan.limits = data.limits
    if data.is_active is not None:
        plan.is_active = data.is_active
    
    await session.commit()
    return plan


@router.post("/companies/{company_id}/activate")
async def activate_subscription(
    company_id: UUID,
    plan_name: PlanName,
    is_yearly: bool = False,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    from datetime import datetime, timedelta
    
    plan_repo = PlanRepository(session)
    plan = await plan_repo.get_by_name(plan_name)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    sub_repo = SubscriptionRepository(session)
    sub = await sub_repo.get_by_company(company_id)
    
    if sub:
        sub.plan_id = plan.id
        sub.status = SubscriptionStatus.ACTIVE
        sub.is_yearly = is_yearly
        sub.current_period_start = datetime.utcnow()
        sub.current_period_end = datetime.utcnow() + timedelta(days=365 if is_yearly else 30)
    else:
        sub = Subscription(
            company_id=company_id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            is_yearly=is_yearly,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=365 if is_yearly else 30),
        )
        session.add(sub)
    
    await session.commit()
    return {"ok": True, "plan": plan_name, "company_id": str(company_id)}
