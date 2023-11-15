from fastapi import HTTPException
from starlette import status


class UnauthenticatedUserError(HTTPException):
    def __init__(self, detail):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
