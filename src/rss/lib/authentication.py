from datetime import datetime
from typing import Any, Mapping, Union
from fastapi import Depends, Request, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.oauth2 import id_token as token_oauth2
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests

from sqlalchemy.orm import Session
from src.rss.models.user import User
from src.rss import deps
from src.rss.view_models import authentication
from src.rss.lib.exceptions.authentication import (
    UnauthenticatedUserError,
)

CLIENT_ID = "210289239482-ln01lnl1b80l2smefebcp5cosofa2ud6.apps.googleusercontent.com"


## JWT Bearer Authentication


def parse_jwt(id_token: str) -> Union[Mapping, None]:
    try:
        user_info: Mapping[str, Any] = token_oauth2.verify_oauth2_token(
            id_token, requests.Request(), CLIENT_ID
        )

    # If no JWT exists, or invalid, prefer emptying credential values
    # over raising an error. A more generic unauthorized user error may
    # be raised later, but this function shouldn't be interested in doing
    # anything besides returning a parsed JWT.
    except GoogleAuthError:
        return None
    except ValueError:
        return None

    return user_info


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: Union[HTTPAuthorizationCredentials, None]

        try:
            credentials = await super(JWTBearer, self).__call__(request)
        except HTTPException:
            credentials = None

        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=403, detail="Invalid authentication scheme."
                )
            token_payload = self.verify_jwt(credentials.credentials)

            if not token_payload:
                raise UnauthenticatedUserError(detail="Invalid or expired id token.")

            return token_payload

        else:
            return None

    @staticmethod
    def verify_jwt(token: str) -> Union[authentication.TokenAuthenticated, None]:
        user_info = parse_jwt(token)
        if user_info is None:
            return user_info

        return authentication.TokenAuthenticated.model_validate(user_info)


## Authentication Deps


async def authenticate_current_user(
    db: Session = Depends(deps.get_db),
    bearer: Union[authentication.TokenAuthenticated, None] = Depends(JWTBearer()),
) -> Union[User, None]:
    # If there is no id_token present with this request, we do not have a current user to authenticate.
    # Note though, that this may not necessitate an error being raised.
    if not bearer:
        return None

    # We add users to the database so long as we can verify their account information.
    # Note that an authenticated user != an authorized user.
    user = db.query(User).filter(User.user_id == bearer.sub).one_or_none()

    if not user:
        user = User(
            user_id=bearer.sub,
            first_name=bearer.given_name,
            last_name=bearer.family_name,
            email=bearer.email,
        )
    else:
        # user_id / sub cannot change. Other values may be updated.
        user.first_name = bearer.given_name
        user.last_name = bearer.family_name
        user.email = bearer.email
        user.last_login = datetime.now()

    db.add(user)
    db.commit()
    return user
