import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Boolean, ForeignKey, Integer, Numeric, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.infrastructure.database.connection import Base
import enum


class PriceType(str, enum.Enum):
    FIXED = "fixed"
    RANGE = "range"
    BY_MAKE = "by_make"
    ON_REQUEST = "on_request"


class ServiceCategory(str, enum.Enum):
    MAINTENANCE = "maintenance"
    DIAGNOSTICS = "diagnostics"
    ENGINE = "engine"
    TRANSMISSION = "transmission"
    SUSPENSION = "suspension"
    BRAKES = "brakes"
    ELECTRICAL = "electrical"
    BODY = "body"
    TIRES = "tires"
    AC = "ac"
    OTHER = "other"


class Service(Base):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[ServiceCategory] = mapped_column(SAEnum(ServiceCategory), default=ServiceCategory.OTHER)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    keywords: Mapped[list] = mapped_column(JSONB, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    company: Mapped["Company"] = relationship(back_populates="services")
    prices: Mapped[list["ServicePrice"]] = relationship(back_populates="service", cascade="all, delete-orphan")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="service")


class ServicePrice(Base):
    __tablename__ = "service_prices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"))
    price_type: Mapped[PriceType] = mapped_column(SAEnum(PriceType), default=PriceType.FIXED)
    fixed_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    prices_by_make: Mapped[dict] = mapped_column(JSONB, default=dict)
    car_make: Mapped[str | None] = mapped_column(String(100))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    service: Mapped["Service"] = relationship(back_populates="prices")
