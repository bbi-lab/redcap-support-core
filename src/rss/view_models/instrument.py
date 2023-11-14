from datetime import datetime
from typing import Optional

from pydantic import ConfigDict

from rss.view_models.base.base import BaseModel
from rss.view_models.project import ProjectEventSimple, ProjectInstrumentSimple


class InstrumentBase(BaseModel):
    id: int
    record_id: int
    event: ProjectEventSimple
    instrument: ProjectInstrumentSimple
    repeat_instance: Optional[int]
    data: dict[str, str]

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class SavedInstrument(InstrumentBase):
    created: datetime
    modified: datetime


class Instrument(SavedInstrument):
    pass
