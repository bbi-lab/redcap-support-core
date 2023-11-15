from datetime import datetime
from typing import Optional, Any
from uuid import UUID

from pydantic import ConfigDict

from rss.view_models.base.base import BaseModel


class ReportBase(BaseModel):
    name: str
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class CreatedReport(ReportBase):
    records: list[int]
    events: list[str]
    instruments: list[str]
    fields: list[str]
    calculated_event_fields: Optional[list[str]]
    calculated_instrument_fields: Optional[list[str]]
    filters: dict[str, Any]


class ModifiedReport(CreatedReport):
    uuid: UUID


class SavedReport(ModifiedReport):
    created: datetime
    modified: datetime


class Report(SavedReport):
    pass
