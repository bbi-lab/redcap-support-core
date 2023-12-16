from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Boolean,
    Integer,
    String,
    ForeignKey,
    Index,
    Table,
)
from sqlalchemy.orm import mapped_column, Mapped, relationship

from rss.db.base import Base


class ProjectArm(Base):
    __tablename__ = "project_arm"  # type: ignore

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    created: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=datetime.now
    )
    modified: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=datetime.now, onupdate=datetime.now()
    )

    events: Mapped[list["ProjectEvent"]] = relationship(
        "ProjectEvent", back_populates="arm"
    )


event_instrument_association = Table(
    "project_event_project_instrument_association",
    Base.metadata,
    Column("project_event_id", ForeignKey("project_event.id"), primary_key=True),
    Column(
        "project_instrument_id", ForeignKey("project_instrument.id"), primary_key=True
    ),
)


class ProjectEvent(Base):
    __tablename__ = "project_event"  # type: ignore
    __table_args__ = (Index("project_event_name_idx", "name", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    arm_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project_arm.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    repeating: Mapped[bool] = mapped_column(Boolean, nullable=False)

    created: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=datetime.now
    )
    modified: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=datetime.now, onupdate=datetime.now()
    )

    arm: Mapped[ProjectArm] = relationship("ProjectArm", back_populates="events")
    instruments: Mapped[list["ProjectInstrument"]] = relationship(
        "ProjectInstrument",
        secondary=event_instrument_association,
        back_populates="events",
    )

    # TODO: In an ideal world, we would have these relationships, but including them
    #       causes some recursion issues when evaluating our pydantic models (events
    #       refer back to these project_events, which then refere back to events, etc.),
    #       causing cyclic recursion errors during Pydantic model validation. If we
    #       could eliminate the recursive behavior of these relationships, we could
    #       reinclude them in our model. See: https://docs.pydantic.dev/latest/usage/postponed_annotations/#cyclic-references
    #
    # event_records = relationship("Event", back_populates="event")
    # instrument_records = relationship("Instrument", back_populates="event")


class ProjectInstrument(Base):
    __tablename__ = "project_instrument"  # type: ignore
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

    events: Mapped[list[ProjectEvent]] = relationship(
        "ProjectEvent",
        secondary=event_instrument_association,
        back_populates="instruments",
    )
    fields: Mapped[list["ProjectField"]] = relationship(
        "ProjectField", back_populates="instrument"
    )

    # See comment above.
    # event_records = relationship("Event", back_populates="instrument")
    # instrument_records = relationship("Instrument", back_populates="instrument")


class ProjectField(Base):
    __tablename__ = "project_field"  # type: ignore
    __table_args__ = (Index("project_field_name_idx", "name", unique=True),)

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

    instrument: Mapped[list[ProjectInstrument]] = relationship(
        "ProjectInstrument", back_populates="fields"
    )
