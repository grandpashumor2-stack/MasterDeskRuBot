from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from decimal import Decimal
from app.domain.models.service import PriceType, ServiceCategory


class ServiceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: ServiceCategory = ServiceCategory.OTHER
    duration_minutes: int = 60
    keywords: list[str] = []


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[ServiceCategory] = None
    duration_minutes: Optional[int] = None
    is_active: Optional[bool] = None
    keywords: Optional[list[str]] = None


class ServicePriceCreate(BaseModel):
    price_type: PriceType = PriceType.FIXED
    fixed_price: Optional[Decimal] = None
    price_min: Optional[Decimal] = None
    price_max: Optional[Decimal] = None
    prices_by_make: Optional[dict[str, float]] = None
    is_default: bool = True


class ServiceResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    category: ServiceCategory
    duration_minutes: int
    is_active: bool
    keywords: list[str]

    model_config = {"from_attributes": True}
