from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models.subscription import Plan, Subscription, Payment, SubscriptionStatus, PlanName
from app.domain.repositories.base import BaseRepository
import uuid


class PlanRepository(BaseRepository[Plan]):
    def __init__(self, session: AsyncSession):
        super().__init__(Plan, session)

    async def get_by_name(self, name: PlanName) -> Optional[Plan]:
        result = await self.session.execute(select(Plan).where(Plan.name == name))
        return result.scalar_one_or_none()

    async def get_active_plans(self) -> List[Plan]:
        result = await self.session.execute(select(Plan).where(Plan.is_active == True))
        return list(result.scalars().all())


class SubscriptionRepository(BaseRepository[Subscription]):
    def __init__(self, session: AsyncSession):
        super().__init__(Subscription, session)

    async def get_by_company(self, company_id: uuid.UUID) -> Optional[Subscription]:
        result = await self.session.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_active_count(self) -> int:
        result = await self.session.execute(
            select(func.count()).where(
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
            )
        )
        return result.scalar()

    async def get_mrr(self) -> float:
        """Calculate Monthly Recurring Revenue."""
        result = await self.session.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.status == SubscriptionStatus.ACTIVE)
        )
        subs = list(result.scalars().all())
        mrr = 0.0
        for sub in subs:
            if sub.is_yearly:
                mrr += float(sub.plan.yearly_price) / 12
            else:
                mrr += float(sub.plan.monthly_price)
        return mrr

    async def get_expired_trials(self) -> List[Subscription]:
        result = await self.session.execute(
            select(Subscription).where(
                and_(
                    Subscription.status == SubscriptionStatus.TRIAL,
                    Subscription.trial_ends_at <= datetime.utcnow(),
                )
            )
        )
        return list(result.scalars().all())
