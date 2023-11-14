# See https://peps.python.org/pep-0563/#forward-references
from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict

from src.rss.view_models.base.base import BaseModel


class ProjectElement(BaseModel):
    id: int
    name: str
    created: datetime
    modified: datetime

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class RepeatingInstrument(ProjectElement):
    repeating: bool


class ProjectArmSimple(ProjectElement):
    pass


class ProjectArm(ProjectArmSimple):
    events: list["ProjectEvent"]


class ProjectEventSimple(RepeatingInstrument):
    pass


class ProjectEvent(ProjectEventSimple):
    arm_id: int
    instruments: list["ProjectInstrument"]


class ProjectInstrumentSimple(RepeatingInstrument):
    pass


class ProjectInstrument(ProjectInstrumentSimple):
    fields: list["ProjectField"]


class ProjectFieldSimple(ProjectElement):
    pass


class ProjectField(ProjectElement):
    instrument_id: int


# Rebuild models depended on by external views
ProjectArm.model_rebuild()
ProjectEvent.model_rebuild()
ProjectInstrument.model_rebuild()
