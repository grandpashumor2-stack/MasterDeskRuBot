from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.infrastructure.database.connection import get_db
from app.core.security import get_current_owner
from app.domain.repositories.appointment import AppointmentRepository

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/{company_id}/summary")
async def get_summary(company_id: UUID, session: AsyncSession = Depends(get_db), current_user=Depends(get_current_owner)):
    repo = AppointmentRepository(session)
    appointments = await repo.get_company_appointments(company_id)
    return {"total": len(appointments), "company_id": str(company_id)}
