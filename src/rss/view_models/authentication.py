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
    azp: str
    email: str
    email_verified: bool
    family_name: str
    given_name: str
    hd: str
    locale: str
    name: str
    picture: str
