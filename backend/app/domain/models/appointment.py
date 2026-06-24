import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Text, Enum as SAEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.infrastructure.database.connection import Base
import enum


class AppointmentStatus(str, enum.Enum):
    PENDING = "pending"         # Ожидает подтверждения
    CONFIRMED = "confirmed"     # Подтверждён
    IN_PROGRESS = "in_progress" # В работе
    COMPLETED = "completed"     # Завершён
    CANCELLED = "cancelled"     # Отменён
    NO_SHOW = "no_show"        # Не явился


class AppointmentSource(str, enum.Enum):
    TELEGRAM_BOT = "telegram_bot"
    WEB_PANEL = "web_panel"
    PHONE = "phone"
    WALK_IN = "walk_in"


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"))
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"))
    service_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("services.id", ondelete="SET NULL"))
    employee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"))
    
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    status: Mapped[AppointmentStatus] = mapped_column(SAEnum(AppointmentStatus, values_callable=lambda x: [e.value for e in x]), default=AppointmentStatus.PENDING)
    source: Mapped[AppointmentSource] = mapped_column(SAEnum(AppointmentSource, values_callable=lambda x: [e.value for e in x]), default=AppointmentSource.TELEGRAM_BOT)
    
    client_phone: Mapped[str | None] = mapped_column(String(20))
    client_name: Mapped[str | None] = mapped_column(String(255))
    car_description: Mapped[str | None] = mapped_column(String(500))
    problem_description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    
    # Reminders
    reminder_24h_sent: Mapped[bool] = mapped_column(default=False)
    reminder_2h_sent: Mapped[bool] = mapped_column(default=False)
    
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    company: Mapped["Company"] = relationship(back_populates="appointments")
    client: Mapped["Client"] = relationship(back_populates="appointments")
    vehicle: Mapped["Vehicle"] = relationship(back_populates="appointments")
    service: Mapped["Service"] = relationship(back_populates="appointments")
    employee: Mapped["Employee"] = relationship(back_populates="appointments")
