from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from datetime import time as Time

from app.infrastructure.database.connection import get_db
from app.core.security import get_current_owner
from app.domain.models.company import Company, WorkingHours
from app.domain.repositories.company import CompanyRepository
from app.api.v1.schemas.company import CompanyUpdate, WorkingHoursCreate

router = APIRouter(prefix="/company", tags=["company"])


@router.get("/me")
async def get_my_company(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    if not current_user.company_id:
        raise HTTPException(status_code=404, detail="No company found")
    
    result = await session.execute(
        select(Company)
        .options(selectinload(Company.working_hours), selectinload(Company.subscription))
        .where(Company.id == current_user.company_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.patch("/me")
async def update_my_company(
    data: CompanyUpdate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    repo = CompanyRepository(session)
    company = await repo.get(current_user.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    company = await repo.update(company, **update_data)
    await session.commit()
    return company


@router.put("/me/working-hours")
async def set_working_hours(
    hours: list[WorkingHoursCreate],
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    company_id = current_user.company_id
    
    # Delete existing
    from sqlalchemy import delete
    await session.execute(delete(WorkingHours).where(WorkingHours.company_id == company_id))
    
    # Insert new
    for h in hours:
        def parse_time(t_str):
            if not t_str:
                return None
            parts = t_str.split(":")
            return Time(int(parts[0]), int(parts[1]))
        
        wh = WorkingHours(
            company_id=company_id,
            day_of_week=h.day_of_week,
            is_working=h.is_working,
            open_time=parse_time(h.open_time),
            close_time=parse_time(h.close_time),
            break_start=parse_time(h.break_start),
            break_end=parse_time(h.break_end),
        )
        session.add(wh)
    
    await session.commit()
    return {"ok": True}


@router.post("/me/bot-token")
async def set_bot_token(
    token: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    """Set Telegram bot token for the company."""
    repo = CompanyRepository(session)
    company = await repo.get(current_user.company_id)
    company.telegram_bot_token = token
    await session.commit()
    return {"ok": True, "message": "Bot token updated. Restart the bot service."}
