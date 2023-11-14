from datetime import datetime
from uuid import uuid4
from typing import Optional, Any

from sqlalchemy import DateTime, String
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy.dialects.postgresql import JSONB, UUID

from rss.db.base import Base


class Report(Base):
    __tablename__ = "report"  # type: ignore

    uuid: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    records: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    events: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    instruments: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    fields: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    calculated_event_fields: Mapped[list[str]] = mapped_column(JSONB, nullable=True)
    calculated_instrument_fields: Mapped[list[str]] = mapped_column(
        JSONB, nullable=True
    )

    created = mapped_column(DateTime, nullable=True, default=datetime.now)
    modified = mapped_column(
        DateTime, nullable=True, default=datetime.now, onupdate=datetime.now()
    )
