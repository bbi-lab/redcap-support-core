from datetime import datetime

from sqlalchemy import DateTime, Integer, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.dialects.postgresql import JSONB

from rss.db.base import Base
from rss.models.project import ProjectEvent, ProjectInstrument


class Event(Base):
    __tablename__ = "event"

    __table_args__ = (
        # All rows must be unique across these four identifiers.
        UniqueConstraint("record_id", "repeat_instance", "event_id", "instrument_id"),
        Index("event_record_id_idx", "record_id"),
        Index("event_event_instrument_idx", "event_id", "instrument_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project_event.id"), nullable=False
    )
    instrument_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project_instrument.id"), nullable=False
    )
    repeat_instance: Mapped[int] = mapped_column(Integer, nullable=True)

    # Map python dict to psql JSONB. Anytime we interact with this column
    # via SQLAlchemy, it will be via dictionary operators.
    data: Mapped[dict] = mapped_column(JSONB, nullable=True)

    created = mapped_column(DateTime, nullable=True, default=datetime.now)
    modified = mapped_column(
        DateTime, nullable=True, default=datetime.now, onupdate=datetime.now()
    )

    # See comment in ./project.py. For now, this is fine as a one way relationship
    event: Mapped[ProjectEvent] = relationship("ProjectEvent")
    instrument: Mapped[ProjectInstrument] = relationship("ProjectInstrument")
