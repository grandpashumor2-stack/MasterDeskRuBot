from pydantic import BaseModel
from typing import Optional
from decimal import Decimal


class ServiceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    duration_minutes: int
    price: Decimal


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    price: Optional[Decimal] = None


class ServicePriceCreate(BaseModel):
    price: Decimal
