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
    return appointment


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

