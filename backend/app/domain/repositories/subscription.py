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
        """Calculate MRR based on the last ACTUALLY PAID payment amount,
        not the live plan price -- stays correct after price changes."""
        from app.domain.models.subscription import Payment, PaymentStatus
        result = await self.session.execute(
            select(Subscription).where(Subscription.status == SubscriptionStatus.ACTIVE)
        )
        subs = list(result.scalars().all())
        mrr = 0.0
        for sub in subs:
            payment_result = await self.session.execute(
                select(Payment)
                .where(Payment.subscription_id == sub.id, Payment.status == PaymentStatus.PAID)
                .order_by(Payment.created_at.desc())
                .limit(1)
            )
            last_payment = payment_result.scalar_one_or_none()
            if not last_payment:
                continue
            if sub.is_yearly:
                mrr += float(last_payment.amount) / 12
            else:
                mrr += float(last_payment.amount)
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
