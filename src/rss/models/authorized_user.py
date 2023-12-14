from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import mapped_column, Mapped, relationship

from rss.db.base import Base


class AuthorizedUser(Base):
    __tablename__ = "authorized_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("user.user_id"), nullable=False
    )

    # Users are unauthorized by default
    viewer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    editor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=datetime.now
    )
    modified: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=datetime.now, onupdate=datetime.now()
    )

    user = relationship("User", back_populates="authorization")
