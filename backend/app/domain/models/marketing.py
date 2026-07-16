import uuid
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.infrastructure.database.connection import Base


class PageEvent(Base):
    """Anonymous marketing funnel tracking.

    Records page views on /demo and /register, plus successful
    registrations — so we can see the real funnel numbers (how many
    people viewed the demo vs. how many actually registered) instead
    of guessing. Not tied to a company: visitors here aren't a
    company yet, that's the whole point of a funnel.
    """
    __tablename__ = "page_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(50))  # 'demo_view' | 'register_view' | 'register_success'
    referral_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
