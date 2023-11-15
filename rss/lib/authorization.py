from fastapi import Depends
from rss.lib.authentication import authenticate_current_user
from rss.models.authorized_user import AuthorizedUser
from rss.models.user import User
from typing import Union
from rss import deps
from sqlalchemy.orm import Session

from rss.lib.exceptions.authorization import UnauthorizedUserError

## Authorization Deps


async def authorize_current_user(
    db: Session = Depends(deps.get_db),
    authenticated_user: Union[User, None] = Depends(authenticate_current_user),
) -> Union[AuthorizedUser, None]:
    # A user cannot be authorized if they are unable to be authenticated.
    if not authenticated_user:
        return None

    authorized_user = (
        db.query(AuthorizedUser)
        .filter(AuthorizedUser.user_id == authenticated_user.user_id)
        .one_or_none()
    )

    # If no authorized user is present, add them with no permission levels. Functionally,
    # this should never provide any more elevated permissions than not being in the db.
    if not authorized_user:
        authorized_user = AuthorizedUser(user_id=authenticated_user.user_id)
        db.add(authorized_user)
        db.commit()

    return authorized_user


## Authorization permission levels.


async def require_authorized_viewer(
    authorized_user: Union[AuthorizedUser, None] = Depends(authorize_current_user),
) -> Union[AuthorizedUser, None]:
    if authorized_user is None:
        raise UnauthorizedUserError(detail="Could not validate credentials")
    elif not authorized_user.viewer:
        raise UnauthorizedUserError(
            detail="User does not have the appropriate authorizations to view this content."
        )

    return authorized_user


async def require_authorized_editor(
    authorized_user: Union[AuthorizedUser, None] = Depends(authorize_current_user),
) -> Union[AuthorizedUser, None]:
    if authorized_user is None:
        raise UnauthorizedUserError(detail="Could not validate credentials")
    elif not authorized_user.editor:
        raise UnauthorizedUserError(
            detail="User does not have the appropriate authorizations to edit this content."
        )

    return authorized_user


async def require_authorized_admin(
    authorized_user: Union[AuthorizedUser, None] = Depends(authorize_current_user),
) -> Union[AuthorizedUser, None]:
    if not authorized_user:
        raise UnauthorizedUserError(detail="Could not validate credentials")
    elif not authorized_user.admin:
        raise UnauthorizedUserError(
            detail="User must be an admin to access this content."
        )

    return authorized_user
