from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class AppointmentCreate(BaseModel):
    service_id: UUID
    client_id: UUID
    scheduled_at: datetime
    notes: Optional[str] = None


class AppointmentUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[str] = None
