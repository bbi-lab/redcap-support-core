from typing import AsyncGenerator, Generator

from arq import create_pool
from redcap.project import Project

from src.rss.db.session import SessionLocal
from src.rss.queue.worker import RedisQueue
from src.rss.lib.redcap_interface import redcap_environment


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
