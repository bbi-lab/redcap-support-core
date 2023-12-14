from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import mapped_column, Mapped, relationship

from rss.db.base import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True)

    created: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=datetime.now
    )
    last_login: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=datetime.now, onupdate=datetime.now()
    )

    authorization = relationship("AuthorizedUser", back_populates="user")
