from pydantic import BaseModel
from typing import Optional
from datetime import time


class WorkingHoursCreate(BaseModel):
    day_of_week: int  # 0=Monday, 6=Sunday
    open_time: time
    close_time: time
    is_working: bool = True


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    timezone: Optional[str] = None
