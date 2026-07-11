import uuid
from datetime import datetime, time
from sqlalchemy import String, Boolean, Integer, ForeignKey, Time, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.infrastructure.database.connection import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    telegram_bot_token: Mapped[str | None] = mapped_column(String(100), unique=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str | None] = mapped_column(String(100))
    referral_code: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_system_prompt: Mapped[str | None] = mapped_column(Text)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    working_hours: Mapped[list["WorkingHours"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    employees: Mapped[list["Employee"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    clients: Mapped[list["Client"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    services: Mapped[list["Service"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    subscription: Mapped["Subscription"] = relationship(back_populates="company", uselist=False)


class WorkingHours(Base):
    __tablename__ = "working_hours"
    __table_args__ = (UniqueConstraint("company_id", "day_of_week"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Mon, 6=Sun
    is_working: Mapped[bool] = mapped_column(Boolean, default=True)
    open_time: Mapped[time | None] = mapped_column(Time)
    close_time: Mapped[time | None] = mapped_column(Time)
    break_start: Mapped[time | None] = mapped_column(Time)
    break_end: Mapped[time | None] = mapped_column(Time)

    company: Mapped["Company"] = relationship(back_populates="working_hours")
