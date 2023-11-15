from fastapi import APIRouter

# Router for handling all interactions with Google OAuth
router = APIRouter(
    prefix="/api/v1/ping",
    tags=["ping"],
    responses={404: {"description": "Not found"}},
)

# Sanity check route
@router.get("/")
async def pong():
    return {"ping": "pong"}
