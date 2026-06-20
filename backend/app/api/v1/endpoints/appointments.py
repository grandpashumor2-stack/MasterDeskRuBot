from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.infrastructure.database.connection import get_db
from app.core.security import get_current_owner
from app.domain.repositories.appointment import AppointmentRepository
from app.api.v1.schemas.appointment import AppointmentCreate, AppointmentUpdate

router = APIRouter(prefix="/appointments", tags=["appointments"])

@router.get("/{company_id}")
async def list_appointments(company_id: UUID, session: AsyncSession = Depends(get_db), current_user=Depends(get_current_owner)):
    repo = AppointmentRepository(session)
    return await repo.get_company_appointments(company_id)

@router.post("/{company_id}")
async def create_appointment(company_id: UUID, data: AppointmentCreate, session: AsyncSession = Depends(get_db), current_user=Depends(get_current_owner)):
    repo = AppointmentRepository(session)
    return await repo.create(company_id=company_id, **data.model_dump())

@router.patch("/{appointment_id}")
async def update_appointment(appointment_id: UUID, data: AppointmentUpdate, session: AsyncSession = Depends(get_db), current_user=Depends(get_current_owner)):
    repo = AppointmentRepository(session)
    return await repo.update(appointment_id, data.model_dump(exclude_none=True))
