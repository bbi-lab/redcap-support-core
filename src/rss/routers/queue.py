from typing import Any, Optional
from arq import ArqRedis
from arq.jobs import JobDef
from fastapi import APIRouter, Depends

from src.rss.deps import get_queue
from src.rss.queue.worker import BACKGROUND_FUNCTIONS, BACKGROUND_CRONJOBS
from src.rss.lib.authorization import (
    require_authorized_viewer,
    require_authorized_admin,
)
from src.rss.models.authorized_user import AuthorizedUser

# Router for handling all interactions with ARQ Worker
router = APIRouter(
    prefix="/api/v1/queue",
    tags=["queue"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/tasks",
    status_code=200,
    response_model=list[str],
    responses={404: {}},
)
async def list_tasks() -> list[str]:
    tasks = [task.__name__ for task in BACKGROUND_FUNCTIONS]
    return tasks


@router.get(
    "/crontasks",
    status_code=200,
    response_model=list[str],
    responses={404: {}},
)
async def list_crontasks():
    tasks = [task for task in BACKGROUND_CRONJOBS]
    return tasks


@router.get(
    "/jobs",
    status_code=200,
    response_model=list[JobDef],
    responses={404: {}},
)
async def get_queued_jobs(
    queue: ArqRedis = Depends(get_queue),
    user: AuthorizedUser = Depends(require_authorized_viewer),
) -> list[JobDef]:
    jobs = await queue.queued_jobs()
    return jobs


@router.get(
    "/jobs/{name}",
    status_code=200,
    response_model=list[JobDef],
    responses={404: {}},
)
async def get_queued_job(
    name: str,
    queue: ArqRedis = Depends(get_queue),
    user: AuthorizedUser = Depends(require_authorized_viewer),
) -> list[JobDef]:
    jobs = [job for job in await queue.queued_jobs() if job.function == name]
    return jobs


@router.post(
    "/enqueue/{name}",
    status_code=200,
    response_model=Any,
    responses={404: {}},
)
async def enqueue(
    name: str,
    timeout: Optional[float] = None,
    queue: ArqRedis = Depends(get_queue),
    user: AuthorizedUser = Depends(require_authorized_admin),
):
    job = await queue.enqueue_job(name)

    # This should only occur if the worker is non-existent. Unknown jobs will
    # raise a distinct error.
    if job is None:
        return None

    return await job.result(timeout=timeout)
