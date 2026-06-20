from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.infrastructure.database.connection import get_db
from app.core.security import get_current_owner
from app.domain.repositories.service import ServiceRepository
from app.api.v1.schemas.service import ServiceCreate, ServiceUpdate

router = APIRouter(prefix="/services", tags=["services"])

@router.get("/{company_id}")
async def list_services(company_id: UUID, session: AsyncSession = Depends(get_db)):
    repo = ServiceRepository(session)
    return await repo.get_company_services(company_id)

@router.post("/{company_id}")
async def create_service(company_id: UUID, data: ServiceCreate, session: AsyncSession = Depends(get_db), current_user=Depends(get_current_owner)):
    repo = ServiceRepository(session)
    return await repo.create(company_id=company_id, **data.model_dump())
