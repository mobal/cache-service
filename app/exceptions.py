from fastapi import HTTPException, status


class KeyValueNotFoundException(HTTPException):
    def __init__(self, detail):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
