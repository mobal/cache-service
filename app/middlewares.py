import uuid
from contextvars import ContextVar

from aws_lambda_powertools import Logger
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import (BaseHTTPMiddleware,
                                       RequestResponseEndpoint)
from starlette.types import ASGIApp

X_API_KEY = "X-Api-Key"
X_CORRELATION_ID = "X-Correlation-ID"

correlation_id: ContextVar[str] = ContextVar(X_CORRELATION_ID)
logger = Logger(utc=True)


class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, api_key: str):
        super().__init__(app)
        self._api_key = api_key

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.headers.get("X-Api-Key") != self._api_key:
            error_message = "Invalid or missing API key"
            logger.warning(error_message)
            return JSONResponse(
                content={"message": error_message},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return await call_next(request)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        correlation_id.set(
            request.headers.get(X_CORRELATION_ID)
            or request.scope.get("aws.context", {}).aws_request_id
            if request.scope.get("aws.context")
            else str(uuid.uuid4())
        )
        logger.set_correlation_id(correlation_id.get())
        response = await call_next(request)
        response.headers[X_CORRELATION_ID] = correlation_id.get()
        return response
