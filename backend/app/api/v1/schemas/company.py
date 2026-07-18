from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime


class CompanyCreate(BaseModel):
    name: str
    slug: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None
    ai_system_prompt: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    max_chat_id: Optional[str] = None


class CompanyResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    phone: Optional[str]
    address: Optional[str]
    city: Optional[str]
    description: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkingHoursCreate(BaseModel):
    day_of_week: int  # 0-6
    is_working: bool
    open_time: Optional[str] = None  # "09:00"
    close_time: Optional[str] = None  # "19:00"
    break_start: Optional[str] = None
    break_end: Optional[str] = None
