from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import mapped_column, Mapped, relationship

from rss.db.base import Base


class ProjectArm(Base):
    __tablename__ = "project_arm"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    created: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=datetime.now
    )
    modified: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=datetime.now, onupdate=datetime.now()
    )

    events = relationship("ProjectEvent", back_populates="arm")
