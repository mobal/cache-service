from aws_lambda_powertools import Logger
from fastapi import Request, Response, status
from starlette.middleware.base import (BaseHTTPMiddleware,
                                       RequestResponseEndpoint)
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

X_API_KEY = "X-Api-Key"


class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, api_key: str):
        super().__init__(app)
        self.__api_key = api_key
        self.__logger = Logger(utc=True)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.headers.get("X-Api-Key") != self.__api_key:
            error_message = "Invalid or missing API key"
            self.__logger.warning(error_message)
            return JSONResponse(
                content={"message": error_message},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return await call_next(request)
