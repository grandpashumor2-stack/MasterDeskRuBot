from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models.company import Company, WorkingHours
from app.domain.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, session: AsyncSession):
        super().__init__(Company, session)

    async def get_by_slug(self, slug: str) -> Optional[Company]:
        result = await self.session.execute(
            select(Company).where(Company.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_by_bot_token(self, token: str) -> Optional[Company]:
        result = await self.session.execute(
            select(Company).where(Company.telegram_bot_token == token)
        )
        return result.scalar_one_or_none()

    async def get_with_relations(self, company_id) -> Optional[Company]:
        result = await self.session.execute(
            select(Company)
            .options(
                selectinload(Company.working_hours),
                selectinload(Company.services),
                selectinload(Company.subscription),
            )
            .where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_active_companies(self) -> List[Company]:
        result = await self.session.execute(
            select(Company).where(Company.is_active == True)
        )
        return list(result.scalars().all())
