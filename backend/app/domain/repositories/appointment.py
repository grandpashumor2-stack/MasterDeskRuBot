from typing import Optional, List
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models.appointment import Appointment, AppointmentStatus
from app.domain.repositories.base import BaseRepository
import uuid


class AppointmentRepository(BaseRepository[Appointment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Appointment, session)

    async def get_company_appointments(
        self, company_id: uuid.UUID,
        status: Optional[AppointmentStatus] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Appointment]:
        q = select(Appointment).where(Appointment.company_id == company_id)
        if status:
            q = q.where(Appointment.status == status)
        if date_from:
            q = q.where(Appointment.scheduled_at >= date_from)
        if date_to:
            q = q.where(Appointment.scheduled_at <= date_to)
        q = q.options(
            selectinload(Appointment.client),
            selectinload(Appointment.service),
            selectinload(Appointment.vehicle),
        ).order_by(Appointment.scheduled_at)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_today_appointments(self, company_id: uuid.UUID) -> List[Appointment]:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        return await self.get_company_appointments(
            company_id, date_from=today_start, date_to=today_end
        )

    async def get_busy_slots(self, company_id: uuid.UUID, target_date: date) -> List[datetime]:
        day_start = datetime(target_date.year, target_date.month, target_date.day)
        day_end = day_start + timedelta(days=1)
        q = select(Appointment).where(
            Appointment.company_id == company_id,
            Appointment.scheduled_at >= day_start,
            Appointment.scheduled_at < day_end,
            Appointment.status != AppointmentStatus.CANCELLED,
        )
        result = await self.session.execute(q)
        appointments = list(result.scalars().all())
        busy = [a.scheduled_at for a in appointments]
        return busy
