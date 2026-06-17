from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models.service import Service, ServicePrice
from app.domain.repositories.base import BaseRepository
import uuid


class ServiceRepository(BaseRepository[Service]):
    def __init__(self, session: AsyncSession):
        super().__init__(Service, session)

    async def get_company_services(self, company_id: uuid.UUID, active_only: bool = True) -> List[Service]:
        q = select(Service).where(Service.company_id == company_id)
        if active_only:
            q = q.where(Service.is_active == True)
        q = q.options(selectinload(Service.prices)).order_by(Service.sort_order, Service.name)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def search_by_keywords(self, company_id: uuid.UUID, keywords: list[str]) -> List[Service]:
        """Find services matching given keywords."""
        services = await self.get_company_services(company_id)
        matched = []
        keywords_lower = [k.lower() for k in keywords]
        for svc in services:
            svc_keywords = [k.lower() for k in (svc.keywords or [])]
            svc_name_lower = svc.name.lower()
            if any(
                kw in svc_name_lower or svc_name_lower in kw or kw in svc_keywords
                for kw in keywords_lower
            ):
                matched.append(svc)
        return matched


class ServicePriceRepository(BaseRepository[ServicePrice]):
    def __init__(self, session: AsyncSession):
        super().__init__(ServicePrice, session)
