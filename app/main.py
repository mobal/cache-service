import logging
import uuid
from typing import List

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi_camelcase import CamelModel
from mangum import Mangum
from pydantic import ValidationError
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import Configuration
from app.schemas import CreateKeyValue
from app.services import CacheService

logger = logging.getLogger()
config = Configuration()

cache_service = CacheService()

app = FastAPI(debug=config.app_stage == 'dev')


@app.get('/api/cache/{key}')
async def get(key: str, request: Request) -> JSONResponse:
    logger.info(f'request={request}')
    return JSONResponse(content=jsonable_encoder(await cache_service.get_key_value_by_key(key)),
                        status_code=status.HTTP_200_OK)


@app.post('/api/cache')
async def put(data: CreateKeyValue, request: Request) -> Response:
    logger.info(f'request={request}')
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
async def http_exception_handler(request: Request, error: HTTPException) -> JSONResponse:
    error_id = uuid.uuid4()
    logger.error(f'{error.detail} with status_code={error.status_code}, error_id={error_id} and request={request}')
    return JSONResponse(
        content=jsonable_encoder(ErrorResponse(status=error.status_code, id=error_id, message=error.detail)),
        status_code=error.status_code
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, error: ValidationError) -> JSONResponse:
    error_id = uuid.uuid4()
    error_message = str(error)
    status_code = status.HTTP_400_BAD_REQUEST
    logger.error(f'{error_message} with status_code={status_code}, error_id={error_id} and request={request}')
    return JSONResponse(
        content=jsonable_encoder(ValidationErrorResponse(status=status_code, id=error_id, message=str(error),
                                                         errors=error.errors())),
        status_code=status_code
    )


@app.exception_handler(Exception)
async def exception_handler(request: Request, error: NameError) -> JSONResponse:
    error_id = uuid.uuid4()
    error_message = str(error)
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.error(f'{error_message} with status_code={status_code}, error_id={error_id} and request={request}')
    return JSONResponse(
        content=jsonable_encoder(ErrorResponse(status=status_code, id=error_id, message=error_message)),
        status_code=status_code
    )


if __name__ == '__main__':
    uvicorn.run('app.main:app', host='localhost', port=3000, reload=True)
