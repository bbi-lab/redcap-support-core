from typing import Optional
from rss.view_models.base.base import BaseModel


class TokenBase(BaseModel):
    id_token: str


# See: https://developers.google.com/identity/openid-connect/openid-connect#server-flow
# Note though, we aren't using server-flow.
class TokenAuthenticated(BaseModel):
    aud: str
    exp: int
    iat: int
    iss: str
    sub: str
    email: str

    azp: Optional[str]
    email_verified: Optional[bool]
    family_name: Optional[str]
    given_name: Optional[str]
    hd: Optional[str]
    name: Optional[str]
    picture: Optional[str]
