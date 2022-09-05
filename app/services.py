from typing import Any, Optional

import pendulum
from aws_lambda_powertools import Logger, Tracer
from fastapi_camelcase import CamelModel

from app.exceptions import KeyValueNotFoundException
from app.repositories import CacheRepository

tracer = Tracer()


class KeyValue(CamelModel):
    key: str
    value: Any
    created_at: str
    ttl: Optional[int]

    @property
    def expired_at(self) -> str:
        return pendulum.from_timestamp(self.ttl).to_iso8601_string()


class CacheService:
    def __init__(self):
        self._logger = Logger()
        self._repository = CacheRepository()

    @tracer.capture_method
    async def get_key_value_by_key(self, key: str) -> Optional[KeyValue]:
        self._logger.info(f'Get value for key={key}')
        item = await self._repository.get_key_value_by_key(key)
        if item is None:
            self._logger.info(f'The requested value was not found for {key=}')
            raise KeyValueNotFoundException('KeyValue was not found')
        return KeyValue.parse_obj(item)

    @tracer.capture_method
    async def create_key_value(self, data: dict):
        expired_at = (
            pendulum.from_timestamp(data.get('ttl')) if data.get('ttl') else None
        )
        data['created_at'] = pendulum.now().to_iso8601_string()
        data['ttl'] = expired_at.int_timestamp if expired_at else None
        await self._repository.create_key_value(data)
        self._logger.info(
            f'Value for key successfully stored until {expired_at=}, {data=}'
        )
