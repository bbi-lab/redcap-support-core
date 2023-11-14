from datetime import datetime

from sqlalchemy import DateTime, Integer, String, ForeignKey, Index
from sqlalchemy.orm import mapped_column, Mapped, relationship

from src.rss.db.base import Base


class ProjectField(Base):
    __tablename__ = "project_field"  # type: ignore

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project_instrument.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)

    created: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=datetime.now
    )
    modified: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=datetime.now, onupdate=datetime.now()
    )

    instrument = relationship("ProjectInstrument", back_populates="fields")

    Index("project_field_name_idx", "name", unique=True)
