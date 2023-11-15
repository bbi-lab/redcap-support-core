from datetime import datetime
from typing import Optional

from pydantic import ConfigDict
from rss.view_models.base.base import BaseModel


## AuthorizedUser objects
#
# Reverse relationship on `User` intentionally excluded. Although
# we may want to expose the authorizations on a User, we shouldn't
# need to work with AuthorizedUser objects directly.
class SavedAuthorization(BaseModel):
    created: datetime
    modified: datetime


class Authorization(SavedAuthorization):
    viewer: bool
    editor: bool
    admin: bool

    model_config = ConfigDict(from_attributes=True)


## User objects
class UserBase(BaseModel):
    user_id: str

    model_config = ConfigDict(from_attributes=True, extra="ignore")


# This class inherits the `ignore` attribute, so by returning
# only an `AnonymousUser` pydantic will strip identifying information
# from a user object. Note this implicit transformation only occurs
# when calling `AnonymousUser.model_construct`, or when this
# view model is specified as the model type of an endpoint.
class AnonymousUser(UserBase):
    created: datetime
    last_login: datetime


class SavedUser(AnonymousUser):
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]


class AuthorizedUser(SavedUser):
    authorization: Authorization


class User(SavedUser):
    pass
