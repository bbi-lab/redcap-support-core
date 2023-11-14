from typing import Union
from fastapi import APIRouter, Depends
from rss.lib.authorization import authorize_current_user
from rss.models.authorized_user import AuthorizedUser

from rss.models.user import User
from rss.view_models import user
from rss.lib.authentication import authenticate_current_user

# Router for handling all interactions with Google OAuth
router = APIRouter(
    prefix="/api/v1/user",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

# Alias for `/auth/verify`, which operates as more as an _internal route.
@router.get(
    "/me",
    response_model=Union[user.SavedUser, None],
    status_code=200,
    responses={404: {}},
)
async def current_user(
    authenticated_user: Union[User, None] = Depends(authenticate_current_user),
) -> Union[User, None]:
    return authenticated_user


# Alias for `/auth/verify`, which operates as more as an _internal route.
@router.get(
    "/me/roles",
    response_model=Union[user.Authorization, None],
    status_code=200,
    responses={404: {}},
)
async def current_user_roles(
    authorized_user: Union[AuthorizedUser, None] = Depends(authorize_current_user),
) -> Union[AuthorizedUser, None]:
    return authorized_user
