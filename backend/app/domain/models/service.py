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
    MAINTENANCE = "maintenance"      # ТО
    DIAGNOSTICS = "diagnostics"     # Диагностика
    ENGINE = "engine"               # Двигатель
    TRANSMISSION = "transmission"   # КПП
    SUSPENSION = "suspension"       # Подвеска
    BRAKES = "brakes"              # Тормоза
    ELECTRICAL = "electrical"      # Электрика
    BODY = "body"                  # Кузов
    TIRES = "tires"                # Шины/колёса
    AC = "ac"                      # Кондиционер
    OTHER = "other"                # Прочее


class Service(Base):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[ServiceCategory] = mapped_column(SAEnum(ServiceCategory, values_callable=lambda x: [e.value for e in x]), default=ServiceCategory.OTHER)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Keywords for AI to match client requests
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
    price_type: Mapped[PriceType] = mapped_column(SAEnum(PriceType, values_callable=lambda x: [e.value for e in x]), default=PriceType.FIXED)
    # For FIXED
    fixed_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    # For RANGE
    price_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    # For BY_MAKE - stored as {"Toyota": 1500, "BMW": 2500, "Mercedes": 3000}
    prices_by_make: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Optional: specific car make this price applies to (for BY_MAKE)
    car_make: Mapped[str | None] = mapped_column(String(100))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    service: Mapped["Service"] = relationship(back_populates="prices")

    def get_price_for_make(self, car_make: str | None) -> str:
        """Returns formatted price string for given car make."""
        if self.price_type == PriceType.FIXED:
            return f"{int(self.fixed_price):,} ₽".replace(",", " ")
        elif self.price_type == PriceType.RANGE:
            return f"от {int(self.price_min):,} до {int(self.price_max):,} ₽".replace(",", " ")
        elif self.price_type == PriceType.BY_MAKE and car_make:
            make_upper = car_make.strip().capitalize()
            if make_upper in self.prices_by_make:
                price = self.prices_by_make[make_upper]
                return f"{int(price):,} ₽".replace(",", " ")
            return None
        return "уточняйте у мастера"
