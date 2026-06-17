from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.repositories.subscription import SubscriptionRepository
from app.domain.models.subscription import Subscription, SubscriptionStatus
import uuid


class SubscriptionChecker:
    def __init__(self, session: AsyncSession):
        self.sub_repo = SubscriptionRepository(session)

    async def get_subscription(self, company_id: uuid.UUID) -> Subscription | None:
        return await self.sub_repo.get_by_company(company_id)

    async def is_active(self, company_id: uuid.UUID) -> bool:
        sub = await self.get_subscription(company_id)
        if not sub:
            return False
        from datetime import datetime
        if sub.status == SubscriptionStatus.TRIAL:
            return sub.trial_ends_at and sub.trial_ends_at > datetime.utcnow()
        return sub.status == SubscriptionStatus.ACTIVE

    async def has_feature(self, company_id: uuid.UUID, feature: str) -> bool:
        sub = await self.get_subscription(company_id)
        if not sub or not sub.plan:
            return False
        return bool(sub.plan.limits.get(feature, False))

    async def can_use_dialog(self, company_id: uuid.UUID) -> bool:
        """Check if company can use another dialog (not exceeded limit)."""
        sub = await self.get_subscription(company_id)
        if not sub or not sub.plan:
            return False
        max_dialogs = sub.plan.limits.get("max_dialogs", 0)
        if max_dialogs == -1:  # Unlimited
            return True
        return sub.dialogs_used < max_dialogs

    async def increment_dialog_count(self, company_id: uuid.UUID) -> None:
        sub = await self.sub_repo.get_by_company(company_id)
        if sub:
            sub.dialogs_used += 1

    def get_upgrade_message(self, current_plan_name: str) -> str:
        upgrades = {
            "start": "💡 Для этой функции нужен тариф *BUSINESS* (5990 ₽/мес). Включает AI, автозапись и рассылки.",
            "business": "💡 Для этой функции нужен тариф *PREMIUM* (11990 ₽/мес). Неограниченные диалоги и API.",
        }
        return upgrades.get(current_plan_name, "Обновите тариф для доступа к этой функции.")
