from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.infrastructure.database.connection import get_db
from app.core.security import get_current_owner
from app.domain.repositories.appointment import AppointmentRepository
from app.domain.models.appointment import AppointmentStatus
from app.api.v1.schemas.appointment import AppointmentCreate, AppointmentUpdate

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("/{company_id}")
async def list_appointments(
    company_id: UUID,
    status: Optional[AppointmentStatus] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    repo = AppointmentRepository(session)
    appointments = await repo.get_company_appointments(
        company_id, status=status, date_from=date_from, date_to=date_to
    )
    return appointments


@router.get("/{company_id}/today")
async def today_appointments(
    company_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    repo = AppointmentRepository(session)
    return await repo.get_today_appointments(company_id)


@router.post("/{company_id}")
async def create_appointment(
    company_id: UUID,
    data: AppointmentCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    repo = AppointmentRepository(session)
    appointment = await repo.create(company_id=company_id, **data.model_dump())
    await session.commit()
    return appointment


@router.patch("/{appointment_id}")
async def update_appointment(
    appointment_id: UUID,
    data: AppointmentUpdate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    repo = AppointmentRepository(session)
    appointment = await repo.get(appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    previous_status = appointment.status

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if data.status == AppointmentStatus.COMPLETED:
        update_data["completed_at"] = datetime.utcnow()
        # Update client visit count
        if appointment.client_id:
            from app.domain.models.client import Client
            client = await session.get(Client, appointment.client_id)
            if client:
                client.visit_count += 1
                client.last_visit_at = datetime.utcnow()
    appointment = await repo.update(appointment, **update_data)
    await session.commit()

    if data.status == AppointmentStatus.CONFIRMED and previous_status != AppointmentStatus.CONFIRMED:
        await _notify_client_confirmed(session, appointment.id)

    return appointment


async def _notify_client_confirmed(session: AsyncSession, appointment_id: UUID):
    """Send a Telegram confirmation message to the client when the shop confirms the booking."""
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select as _select
    from app.domain.models.appointment import Appointment as AppointmentModel
    from app.domain.models.company import Company
    from app.core.config import settings
    from aiogram import Bot
    import logging

    result = await session.execute(
        _select(AppointmentModel)
        .options(selectinload(AppointmentModel.client), selectinload(AppointmentModel.service))
        .where(AppointmentModel.id == appointment_id)
    )
    apt = result.scalar_one_or_none()
    if not apt or not apt.client or not apt.client.telegram_id:
        return

    company = await session.get(Company, apt.company_id)
    if not company:
        return

    token = company.telegram_bot_token or settings.BOT_TOKEN
    if not token:
        return

    text = (
        f"✅ *Ваша запись подтверждена!*\n\n"
        f"📅 {apt.scheduled_at.strftime('%d.%m.%Y в %H:%M')}\n"
    )
    if apt.service:
        text += f"🔧 {apt.service.name}\n"
    text += f"🏢 {company.name}\n"
    if company.address:
        text += f"📍 {company.address}\n"
    if company.phone:
        text += f"📞 {company.phone}\n"
    text += "\nЖдём вас!"

    try:
        bot = Bot(token=token)
        await bot.send_message(apt.client.telegram_id, text, parse_mode="Markdown")
        await bot.session.close()
    except Exception as e:
        logging.getLogger(__name__).error(f"Confirm notify error: {e}")


@router.get("/{company_id}/stats")
async def appointment_stats(
    company_id: UUID,
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    repo = AppointmentRepository(session)
    return await repo.get_stats(company_id, days=days)

@router.post("")
async def create_appointment(
    data: AppointmentCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    repo = AppointmentRepository(session)
    from app.domain.models.appointment import AppointmentSource
    apt = await repo.create(
        company_id=current_user.company_id,
        client_id=None,
        service_id=data.service_id,
        scheduled_at=data.scheduled_at,
        duration_minutes=60,
        client_phone=data.client_phone,
        client_name=data.client_name,
        car_description=data.car_description,
        source=AppointmentSource.WEB_PANEL,
    )
    return apt

