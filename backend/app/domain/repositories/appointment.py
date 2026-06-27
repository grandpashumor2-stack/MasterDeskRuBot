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


    async def create(self, company_id, client_id, service_id, scheduled_at,
                     duration_minutes=60, client_phone=None, client_name=None,
                     car_description=None, source=None) -> Appointment:
        from app.domain.models.appointment import AppointmentStatus
        appointment = Appointment(
            company_id=company_id,
            client_id=client_id,
            service_id=service_id,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            client_phone=client_phone,
            client_name=client_name,
            car_description=car_description,
            source=source,
            status=AppointmentStatus.PENDING,
        )
        self.session.add(appointment)
        await self.session.commit()
        await self.session.refresh(appointment)
        return appointment

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
        return await self.get_company_appointments(company_id, date_from=today_start, date_to=today_end)

    async def get_busy_slots(self, company_id: uuid.UUID, target_date: date) -> List[datetime]:
        """Get booked time slots for a specific date."""
        day_start = datetime(target_date.year, target_date.month, target_date.day)
        day_end = day_start + timedelta(days=1)
        result = await self.session.execute(
            select(Appointment.scheduled_at).where(
                and_(
                    Appointment.company_id == company_id,
                    Appointment.scheduled_at >= day_start,
                    Appointment.scheduled_at < day_end,
                    Appointment.status.notin_([AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]),
                )
            )
        )
        return list(result.scalars().all())

    async def get_pending_reminders(self) -> List[Appointment]:
        """Get appointments needing reminders."""
        now = datetime.utcnow()
        # 24h reminder: appointments in 23-25h
        reminder_24h_from = now + timedelta(hours=23)
        reminder_24h_to = now + timedelta(hours=25)
        # 2h reminder: appointments in 1.5-2.5h
        reminder_2h_from = now + timedelta(minutes=90)
        reminder_2h_to = now + timedelta(minutes=150)

        result = await self.session.execute(
            select(Appointment)
            .options(selectinload(Appointment.client), selectinload(Appointment.service))
            .where(
                and_(
                    Appointment.status == AppointmentStatus.CONFIRMED,
                    (
                        (
                            Appointment.scheduled_at.between(reminder_24h_from, reminder_24h_to)
                            & (Appointment.reminder_24h_sent == False)
                        ) |
                        (
                            Appointment.scheduled_at.between(reminder_2h_from, reminder_2h_to)
                            & (Appointment.reminder_2h_sent == False)
                        )
                    )
                )
            )
        )
        return list(result.scalars().all())

    async def count_by_status(self, company_id: uuid.UUID, status: AppointmentStatus) -> int:
        result = await self.session.execute(
            select(func.count()).where(
                and_(Appointment.company_id == company_id, Appointment.status == status)
            )
        )
        return result.scalar()

    async def get_stats(self, company_id: uuid.UUID, days: int = 30) -> dict:
        since = datetime.utcnow() - timedelta(days=days)
        total_result = await self.session.execute(
            select(func.count()).where(
                and_(Appointment.company_id == company_id, Appointment.created_at >= since)
            )
        )
        completed_result = await self.session.execute(
            select(func.count()).where(
                and_(
                    Appointment.company_id == company_id,
                    Appointment.status == AppointmentStatus.COMPLETED,
                    Appointment.created_at >= since,
                )
            )
        )
        return {
            "total": total_result.scalar(),
            "completed": completed_result.scalar(),
        }
