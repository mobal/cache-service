import logging
import uuid
from typing import List

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi_camelcase import CamelModel
from mangum import Mangum
from pydantic import ValidationError
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.settings import Settings
from app.schemas import CreateKeyValue
from app.services import CacheService, KeyValue

logger = logging.getLogger()
config = Settings()

cache_service = CacheService()

app = FastAPI(debug=config.app_stage == 'dev')


@app.get('/api/cache/{key}', status_code=status.HTTP_200_OK)
async def get(key: str) -> KeyValue:
    key_value = await cache_service.get_key_value_by_key(key)
    if not key_value:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f'The requested key value pair was not found with key {key}')
    return key_value


@app.post('/api/cache')
async def put(data: CreateKeyValue):
    await cache_service.put_key_value(data.dict())
    return Response(status_code=status.HTTP_201_CREATED)


handler = Mangum(app)


class ErrorResponse(CamelModel):
    status: int
    id: uuid.UUID
    message: str


class ValidationErrorResponse(ErrorResponse):
    errors: List[dict]


@app.exception_handler(HTTPException)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, error: HTTPException) -> JSONResponse:
    error_id = uuid.uuid4()
    logger.error(
        f'{error.detail} with status_code={error.status_code}, error_id={error_id}')
    return JSONResponse(
        content=jsonable_encoder(
            ErrorResponse(
                status=error.status_code,
                id=error_id,
                message=error.detail)),
        status_code=error.status_code)


@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, error: ValidationError) -> JSONResponse:
    error_id = uuid.uuid4()
    error_message = str(error)
    status_code = status.HTTP_400_BAD_REQUEST
    logger.error(
        f'{error_message} with status_code={status_code}, error_id={error_id}')
    return JSONResponse(
        content=jsonable_encoder(
            ValidationErrorResponse(
                status=status_code,
                id=error_id,
                message=str(error),
                errors=error.errors())),
        status_code=status_code)


if __name__ == '__main__':
    uvicorn.run('app.main:app', host='localhost', port=3000, reload=True)
