from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.domain.models.appointment import AppointmentStatus, AppointmentSource


class AppointmentCreate(BaseModel):
    client_id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    employee_id: Optional[UUID] = None
    scheduled_at: datetime
    duration_minutes: int = 60
    client_phone: Optional[str] = None
    client_name: Optional[str] = None
    car_description: Optional[str] = None
    problem_description: Optional[str] = None
    source: AppointmentSource = AppointmentSource.WEB_PANEL


class AppointmentUpdate(BaseModel):
    status: Optional[AppointmentStatus] = None
    scheduled_at: Optional[datetime] = None
    employee_id: Optional[UUID] = None
    notes: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: UUID
    scheduled_at: datetime
    status: AppointmentStatus
    source: AppointmentSource
    client_name: Optional[str]
    client_phone: Optional[str]
    car_description: Optional[str]
    duration_minutes: int
    created_at: datetime

    model_config = {"from_attributes": True}
