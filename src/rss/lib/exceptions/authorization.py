from fastapi import HTTPException
from starlette import status


class UnauthorizedUserError(HTTPException):
    def __init__(self, detail):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
