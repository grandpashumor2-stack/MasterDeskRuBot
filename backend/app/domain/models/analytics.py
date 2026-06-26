import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.infrastructure.database.connection import Base
import enum


class EventType(str, enum.Enum):
    MESSAGE_RECEIVED = "message_received"
    APPOINTMENT_CREATED = "appointment_created"
    APPOINTMENT_COMPLETED = "appointment_completed"
    APPOINTMENT_CANCELLED = "appointment_cancelled"
    CLIENT_RETURNED = "client_returned"
    CAMPAIGN_SENT = "campaign_sent"
    PRICE_REQUESTED = "price_requested"


class AnalyticsEvent(Base):
    __tablename__ = "analytics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    event_type: Mapped[EventType] = mapped_column(SAEnum(EventType, values_callable=lambda x: [e.value for e in x]))
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
