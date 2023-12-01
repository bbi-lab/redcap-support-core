from typing import Optional, Generic, TypeVar, List
from pydantic import AnyHttpUrl

from rss.view_models.base.base import BaseModel


M = TypeVar("M")


class PaginatedResponse(BaseModel, Generic[M]):
    pages: int
    count: int
    items: List[M]
    next_page: Optional[AnyHttpUrl]
    previous_page: Optional[AnyHttpUrl]
