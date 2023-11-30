from typing import AsyncGenerator, Callable, Generator, Optional

from arq import create_pool
from fastapi import Query as FAQuery
from redcap.project import Project
from sqlalchemy.orm import Session, Query

from rss.db.session import SessionLocal
from rss.models.event import Event
from rss.models.instrument import Instrument
from rss.rqueue.worker import RedisQueue
from rss.lib.redcap_interface import redcap_environment
from rss.view_models import event, instrument

########################################################
# Core Dependencies
########################################################


class PaginatedParams:
    def __init__(
        self, page: int = FAQuery(1, ge=1), per_page: int = FAQuery(2500, ge=0)
    ):
        self.page = page
        self.per_page = per_page
        self.limit = per_page * page
        self.offset = (page - 1) * per_page


def get_db() -> Generator:
    db = SessionLocal()
    # db.current_user_id = None
    try:
        yield db
    finally:
        db.close()


def get_project() -> Generator:
    api_url, api_key = redcap_environment()
    project = Project(api_url, api_key)
    try:
        yield project
    finally:
        project = None


async def get_queue() -> AsyncGenerator:
    queue = await create_pool(RedisQueue)
    try:
        yield queue
    finally:
        await queue.close()


########################################################
# Overrideable Dependencies
########################################################


def get_event_calculator() -> (
    Optional[Callable[[Session, Query[Event], list[str]], list[event.Event]]]
):
    return None


def get_instrument_calculator() -> (
    Optional[
        Callable[[Session, Query[Instrument], list[str]], list[instrument.Instrument]]
    ]
):
    return None
