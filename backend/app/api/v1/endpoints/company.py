from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.infrastructure.database.connection import get_db
from app.core.security import get_current_owner
from app.domain.repositories.company import CompanyRepository
from app.api.v1.schemas.company import CompanyUpdate, WorkingHoursCreate

router = APIRouter(prefix="/company", tags=["company"])

@router.get("/me")
async def get_my_company(session: AsyncSession = Depends(get_db), current_user=Depends(get_current_owner)):
    repo = CompanyRepository(session)
    company = await repo.get_by_owner(current_user.id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.patch("/me")
async def update_company(data: CompanyUpdate, session: AsyncSession = Depends(get_db), current_user=Depends(get_current_owner)):
    repo = CompanyRepository(session)
    return await repo.update_by_owner(current_user.id, data.model_dump(exclude_none=True))

@router.post("/me/working-hours")
async def set_working_hours(data: WorkingHoursCreate, session: AsyncSession = Depends(get_db), current_user=Depends(get_current_owner)):
    repo = CompanyRepository(session)
    return await repo.set_working_hours(current_user.id, data.model_dump())
