import os
from arq.connections import RedisSettings
from arq import cron  # noqa: F401

from rss.rqueue.tasks import dummy_task

# ARQ requires at least one task on startup.
BACKGROUND_FUNCTIONS = [dummy_task]
BACKGROUND_CRONJOBS = []

REDIS_IP = os.getenv("REDIS_IP") or "localhost"
REDIS_PORT = int(os.getenv("REDIS_PORT") or 6379)


RedisQueue = RedisSettings(host=REDIS_IP, port=REDIS_PORT)


# TODO: If we need to define custom startup and shutdown behavior
#       on our worker, we can do so here.
async def startup(ctx):
    pass


async def shutdown(ctx):
    pass


class WorkerSettings:
    """
    Settings for the ARQ worker.
    """

    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisQueue
    functions: list = BACKGROUND_FUNCTIONS
    cron_jobs: list = BACKGROUND_CRONJOBS
