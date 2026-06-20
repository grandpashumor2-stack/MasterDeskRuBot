from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.infrastructure.database.connection import get_db
from app.core.security import get_current_owner
from app.domain.repositories.service import ServiceRepository, ServicePriceRepository
from app.domain.models.service import Service, ServicePrice
from app.api.v1.schemas.service import ServiceCreate, ServiceUpdate, ServicePriceCreate

router = APIRouter(prefix="/services", tags=["services"])


@router.get("/{company_id}")
async def list_services(
    company_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    if str(current_user.company_id) != str(company_id):
        from app.domain.models.user import Role
        if current_user.role != Role.PLATFORM_ADMIN:
            raise HTTPException(status_code=403, detail="Access denied")
    
    repo = ServiceRepository(session)
    services = await repo.get_company_services(company_id, active_only=False)
    return services


@router.post("/{company_id}")
async def create_service(
    company_id: UUID,
    data: ServiceCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    repo = ServiceRepository(session)
    service = await repo.create(
        company_id=company_id,
        **data.model_dump()
    )
    await session.commit()
    return service


@router.put("/{service_id}")
async def update_service(
    service_id: UUID,
    data: ServiceUpdate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    repo = ServiceRepository(session)
    service = await repo.get(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    service = await repo.update(service, **update_data)
    await session.commit()
    return service


@router.post("/{service_id}/prices")
async def set_service_price(
    service_id: UUID,
    data: ServicePriceCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    # Remove existing prices if setting default
    from sqlalchemy import delete
    from app.domain.models.service import ServicePrice
    if data.is_default:
        await session.execute(delete(ServicePrice).where(ServicePrice.service_id == service_id))
    
    price = ServicePrice(service_id=service_id, **data.model_dump())
    session.add(price)
    await session.commit()
    await session.refresh(price)
    return price


@router.delete("/{service_id}")
async def delete_service(
    service_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    repo = ServiceRepository(session)
    service = await repo.get(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    await repo.delete(service)
    await session.commit()
    return {"ok": True}
