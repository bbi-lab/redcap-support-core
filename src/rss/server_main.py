import logging

import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.rss.routers import (
    report,
    project,
    authentication,
    user,
    ping,
    queue,
)

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

app.include_router(ping.router)
app.include_router(queue.router)
app.include_router(authentication.router)
app.include_router(report.router)
app.include_router(project.router)
app.include_router(user.router)


# If the application is not already being run within a uvicorn server, start it here.
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
