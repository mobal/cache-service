import uuid

import uvicorn
from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging.logger import set_package_logger
from botocore.exceptions import BotoCoreError
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from mangum import Mangum
from pydantic import Field

from app import settings
from app.middlewares import APIKeyMiddleware, CorrelationIdMiddleware
from app.schemas import CreateKeyValue
from app.services import CacheService, CamelModel, KeyValue

if settings.debug:
    set_package_logger()

logger = Logger(utc=True)
cache_service = CacheService()

app = FastAPI(debug=settings.debug, title="CacheApplication", version="1.0.0")
app.add_middleware(APIKeyMiddleware, api_key=settings.api_key)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(GZipMiddleware)

handler = Mangum(app)
handler = logger.inject_lambda_context(handler, clear_state=True, log_event=True)


@app.get("/api/cache/{key}", status_code=status.HTTP_200_OK)
def get_cache(key: str) -> KeyValue | None:
    return cache_service.get_key_value_by_key(key)


@app.post("/api/cache")
def create_cache(data: CreateKeyValue):
    cache_service.create_key_value(data.model_dump())
    return Response(status_code=status.HTTP_201_CREATED)


class ErrorResponse(CamelModel):
    status: int
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    message: str


class ValidationErrorResponse(ErrorResponse):
    errors: list[dict]


@app.exception_handler(BotoCoreError)
@app.exception_handler(Exception)
def botocore_error_handler(request: Request, error: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception reached global exception handler",
        extra={"path": request.url.path, "method": request.method},
    )
    logger.exception(
        "Unhandled exception",
        extra={
            "exception_type": type(error).__name__,
            "exception_message": str(error),
            "exception_repr": repr(error),
            "exception_cause": repr(error.__cause__) if error.__cause__ else None,
            "exception_context": (
                repr(error.__context__) if error.__context__ else None
            ),
            "path": request.url.path,
            "method": request.method,
        },
    )
    if settings.debug:
        error_message = (
            f"{type(error).__name__}: {str(error) or repr(error)}"
            if str(error)
            else repr(error)
        )
    else:
        error_message = "Internal Server Error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return JSONResponse(
        content=ErrorResponse(status=status_code, message=error_message).model_dump(
            by_alias=True, mode="json"
        ),
        status_code=status_code,
    )


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, error: HTTPException) -> JSONResponse:
    logger.warning(
        "HTTP exception handled",
        extra={"status_code": error.status_code, "path": request.url.path},
    )
    logger.exception(error)

    return JSONResponse(
        content=ErrorResponse(
            status=error.status_code, message=error.detail
        ).model_dump(by_alias=True, mode="json"),
        status_code=error.status_code,
    )


@app.exception_handler(RequestValidationError)
def request_validation_error_handler(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    logger.warning(
        "Request validation error handled",
        extra={"path": request.url.path, "method": request.method},
    )
    logger.exception(error)
    status_code = status.HTTP_400_BAD_REQUEST

    return JSONResponse(
        content=ValidationErrorResponse(
            status=status_code,
            message="Validation Error",
            errors=error.errors(),
        ).model_dump(by_alias=True, mode="json"),
        status_code=status_code,
    )


@app.get("/health")
async def health_check():
    logger.debug("Health check endpoint called")
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("app.api_handler:app", host="localhost", port=3000, reload=True)
