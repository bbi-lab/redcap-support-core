from typing import AsyncGenerator, Callable, Generator, Optional

from arq import create_pool
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
    Optional[
        Callable[[Session, Query[Event], list[str]], list[event.Event]]
    ]
):
    return None


def get_instrument_calculator() -> (
    Optional[
        Callable[[Session, Query[Instrument], list[str]], list[instrument.Instrument]]
    ]
):
    return None
