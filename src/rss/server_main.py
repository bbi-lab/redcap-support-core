import logging

import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from requests import Request
from starlette import status
from starlette.responses import JSONResponse
from rss.lib.middlewares import PaginationMiddleware
from rss.routers import (
    report,
    project,
    authentication,
    user,
    ping,
    queue,
)
from rss.lib.exceptions.report import NoCustomCalculatorError

logging.basicConfig()
# Un-comment this line to log all database queries:
# logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(PaginationMiddleware)

app.include_router(ping.router)
app.include_router(queue.router)
app.include_router(authentication.router)
app.include_router(report.router)
app.include_router(project.router)
app.include_router(user.router)


@app.exception_handler(NoCustomCalculatorError)
async def validation_exception_handler(request: Request, exc: NoCustomCalculatorError):
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, content={"message": str(exc)}
    )


# If the application is not already being run within a uvicorn server, start it here.
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
