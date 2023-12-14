from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Boolean, Index
from sqlalchemy.orm import mapped_column, Mapped, relationship

from rss.db.base import Base
from rss.models.project_event import event_instrument_association


class ProjectInstrument(Base):
    __tablename__ = "project_instrument"
    __table_args__ = (Index("project_instrument_name_idx", "name", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    repeating: Mapped[bool] = mapped_column(Boolean, nullable=False)

    created: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=datetime.now
    )
    modified: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=datetime.now, onupdate=datetime.now()
    )

    events = relationship(
        "ProjectEvent",
        secondary=event_instrument_association,
        back_populates="instruments",
    )
    fields = relationship("ProjectField", back_populates="instrument")

    # See comment in ./project_event.py
    # event_records = relationship("Event", back_populates="instrument")
    # instrument_records = relationship("Instrument", back_populates="instrument")
