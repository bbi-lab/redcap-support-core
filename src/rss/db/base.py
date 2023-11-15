from typing import Any, Dict

from sqlalchemy.orm import DeclarativeBase

class_registry: Dict = {}


class Base(DeclarativeBase):
    id: Any
    __name__: str

    # Generate __tablename__ automatically
    @classmethod
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
