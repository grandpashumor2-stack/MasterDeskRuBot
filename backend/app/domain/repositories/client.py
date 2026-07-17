from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models.client import Client
from app.domain.repositories.base import BaseRepository
import uuid


class ClientRepository(BaseRepository[Client]):
    def __init__(self, session: AsyncSession):
        super().__init__(Client, session)

    async def get_by_telegram_id(self, company_id: uuid.UUID, telegram_id: str) -> Optional[Client]:
        result = await self.session.execute(
            select(Client).where(
                and_(Client.company_id == company_id, Client.telegram_id == telegram_id)
            ).options(selectinload(Client.vehicles))
            async def get_by_max_id(self, company_id: uuid.UUID, max_id: str) -> Optional[Client]:
        result = await self.session.execute(
            select(Client).where(
                and_(Client.company_id == company_id, Client.max_id == max_id)
            ).options(selectinload(Client.vehicles))
        )
        return result.scalar_one_or_none()
        )
        return result.scalar_one_or_none()

    async def get_company_clients(self, company_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Client]:
        result = await self.session.execute(
            select(Client)
            .where(Client.company_id == company_id)
            .offset(skip).limit(limit)
            .order_by(Client.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_clients_for_return_campaign(
        self, company_id: uuid.UUID, days_since_visit: int
    ) -> List[Client]:
        """Get clients who haven't visited for N days."""
        cutoff = datetime.utcnow() - timedelta(days=days_since_visit)
        result = await self.session.execute(
            select(Client).where(
                and_(
                    Client.company_id == company_id,
                    Client.last_visit_at <= cutoff,
                    Client.telegram_id.isnot(None),
                )
            )
        )
        return list(result.scalars().all())

    async def get_by_segment(self, company_id: uuid.UUID, segment_filter: dict) -> List[Client]:
        """Filter clients by segment for campaigns."""
        q = select(Client).where(Client.company_id == company_id)
        if "min_visits" in segment_filter:
            q = q.where(Client.visit_count >= segment_filter["min_visits"])
        if "last_visit_days" in segment_filter:
            cutoff = datetime.utcnow() - timedelta(days=segment_filter["last_visit_days"])
            q = q.where(Client.last_visit_at <= cutoff)
        # Only clients with telegram_id can receive campaigns
        q = q.where(Client.telegram_id.isnot(None))
        result = await self.session.execute(q)
        return list(result.scalars().all())
