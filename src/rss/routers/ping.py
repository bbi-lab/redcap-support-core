from fastapi import APIRouter
from typing import Literal

# Router for handling all interactions with Google OAuth
router = APIRouter(
    prefix="/api/v1/ping",
    tags=["ping"],
    responses={404: {"description": "Not found"}},
)

# Sanity check route
@router.get(
    "",
    status_code=200,
    response_model=dict[Literal["ping"], Literal["pong"]],
    responses={404: {}},
)
async def pong() -> dict[Literal["ping"], Literal["pong"]]:
    return {"ping": "pong"}
