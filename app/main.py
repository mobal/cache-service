import uuid

import uvicorn
from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging.logger import set_package_logger
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from mangum import Mangum
from pydantic import ValidationError

from app import settings
from app.middlewares import APIKeyMiddleware
from app.schemas import CreateKeyValue
from app.services import CacheService, CamelModel, KeyValue

if settings.debug:
    set_package_logger()

logger = Logger(utc=True)
cache_service = CacheService()

app = FastAPI(debug=settings.debug, title="CacheApplication", version="1.0.0")
app.add_middleware(APIKeyMiddleware, api_key=settings.api_key)
app.add_middleware(GZipMiddleware)

handler = Mangum(app)
handler = logger.inject_lambda_context(handler, clear_state=True, log_event=True)


@app.get("/api/cache/{key}", status_code=status.HTTP_200_OK)
async def get_cache(key: str) -> KeyValue | None:
    return cache_service.get_key_value_by_key(key)


@app.post("/api/cache")
async def create_cache(data: CreateKeyValue):
    cache_service.create_key_value(data.model_dump())
    return Response(status_code=status.HTTP_201_CREATED)


class ErrorResponse(CamelModel):
    status: int
    id: uuid.UUID
    message: str


class ValidationErrorResponse(ErrorResponse):
    errors: list[dict]


@app.exception_handler(BotoCoreError)
@app.exception_handler(ClientError)
@app.exception_handler(Exception)
async def error_handler(request: Request, error) -> JSONResponse:
    error_id = uuid.uuid4()
    error_message = str(error)
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.error(f"{error_message} with {status_code=} and {error_id=}")
    return JSONResponse(
        content=jsonable_encoder(
            ErrorResponse(status=status_code, id=error_id, message=error_message)
        ),
        status_code=status_code,
    )


@app.exception_handler(HTTPException)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, error: HTTPException
) -> JSONResponse:
    error_id = uuid.uuid4()
    logger.error(
        f"{error.detail} with status_code={error.status_code} and error_id={error_id}"
    )
    return JSONResponse(
        content=jsonable_encoder(
            ErrorResponse(status=error.status_code, id=error_id, message=error.detail)
        ),
        status_code=error.status_code,
    )


@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
async def validation_error_handler(
    request: Request, error: ValidationError
) -> JSONResponse:
    error_id = uuid.uuid4()
    error_message = str(error)
    status_code = status.HTTP_400_BAD_REQUEST
    logger.error(
        f"{error_message} with status_code={status_code} and error_id={error_id}"
    )
    return JSONResponse(
        content=jsonable_encoder(
            ValidationErrorResponse(
                status=status_code,
                id=error_id,
                message=str(error),
                errors=error.errors(),
            )
        ),
        status_code=status_code,
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="localhost", port=3000, reload=True)
