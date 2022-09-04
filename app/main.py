import uuid
from typing import List

import uvicorn
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi_camelcase import CamelModel
from mangum import Mangum
from pydantic import ValidationError
from starlette import status
from starlette.exceptions import (
    HTTPException as StarletteHTTPException,
    ExceptionMiddleware,
)
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.schemas import CreateKeyValue
from app.services import CacheService, KeyValue

app = FastAPI(debug=True)
app.add_middleware(GZipMiddleware)
app.add_middleware(ExceptionMiddleware, handlers=app.exception_handlers)

logger = Logger()
metrics = Metrics()
tracer = Tracer()
cache_service = CacheService()

handler = Mangum(app)
handler.__name__ = 'handler'
handler = tracer.capture_lambda_handler(handler)
handler = logger.inject_lambda_context(handler, clear_state=True)
handler = metrics.log_metrics(handler, capture_cold_start_metric=True)


@app.get('/api/cache/{key}', status_code=status.HTTP_200_OK)
async def get(key: str) -> KeyValue:
    key_value = await cache_service.get_key_value_by_key(key)
    if not key_value:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f'The requested key value pair was not found with key {key}',
        )
    metrics.add_metric(name='Get', unit=MetricUnit.Count, value=1)
    return key_value


@app.post('/api/cache')
async def put(data: CreateKeyValue):
    await cache_service.put_key_value(data.dict())
    metrics.add_metric(name='Put', unit=MetricUnit.Count, value=1)
    return Response(status_code=status.HTTP_201_CREATED)


class ErrorResponse(CamelModel):
    status: int
    id: uuid.UUID
    message: str


class ValidationErrorResponse(ErrorResponse):
    errors: List[dict]


@app.middleware('http')
async def correlation_id_middleware(request: Request, call_next) -> Response:
    correlation_id = request.headers.get('X-Correlation-ID')
    if not correlation_id:
        correlation_id = (
            request.scope['aws_context'].aws_request_id
            if request.scope.get('aws_context')
            else str(uuid.uuid4())
        )
    logger.set_correlation_id(correlation_id)
    tracer.put_annotation(key='correlation_id', value=correlation_id)
    response = await call_next(request)
    response.headers['X-Correlation-ID'] = correlation_id
    return response


@app.exception_handler(BotoCoreError)
@app.exception_handler(ClientError)
@app.exception_handler(Exception)
async def error_handler(request: Request, error) -> JSONResponse:
    error_id = uuid.uuid4()
    error_message = str(error)
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.error(f'{error_message} with {status_code=} and {error_id=}')
    metrics.add_metric(name='ErrorHandler', unit=MetricUnit.Count, value=1)
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
        f'{error.detail} with status_code={error.status_code} and error_id={error_id}'
    )
    metrics.add_metric(name='HttpExceptionHandler', unit=MetricUnit.Count, value=1)
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
        f'{error_message} with status_code={status_code} and error_id={error_id}'
    )
    metrics.add_metric(name='ValidationErrorHandler', unit=MetricUnit.Count, value=1)
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


if __name__ == '__main__':
    uvicorn.run('app.main:app', host='localhost', port=3000, reload=True)
