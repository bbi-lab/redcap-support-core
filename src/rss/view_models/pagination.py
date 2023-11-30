from typing import Optional, Generic, TypeVar, List
from pydantic import AnyHttpUrl, BaseModel


M = TypeVar("M")


class PaginatedResponse(BaseModel, Generic[M]):
    count: int
    items: List[M]
    next_page: Optional[AnyHttpUrl]
    previous_page: Optional[AnyHttpUrl]
