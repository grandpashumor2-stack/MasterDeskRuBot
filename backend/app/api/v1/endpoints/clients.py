from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.infrastructure.database.connection import get_db
from app.core.security import get_current_owner
from app.domain.repositories.client import ClientRepository

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("/{company_id}")
async def list_clients(
    company_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    repo = ClientRepository(session)
    return await repo.get_company_clients(company_id, skip=skip, limit=limit)
