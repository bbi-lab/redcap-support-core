from fastapi import APIRouter, Depends

from rss.models.user import User
from rss.view_models import user
from rss.lib.authentication import authenticate_current_user

# Router for handling all interactions with Google OAuth
router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/verify",
    response_model=user.SavedUser,
    status_code=200,
    responses={404: {}},
)
async def verify(user: User = Depends(authenticate_current_user)) -> User:
    return user
