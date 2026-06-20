from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.infrastructure.database.connection import get_db
from app.core.security import get_current_owner

router = APIRouter(prefix="/payments", tags=["payments"])

@router.get("/{company_id}")
async def list_payments(company_id: UUID, session: AsyncSession = Depends(get_db), current_user=Depends(get_current_owner)):
    return []
