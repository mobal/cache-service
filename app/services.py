from typing import Any, Optional

import boto3
import pendulum
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key
from fastapi_camelcase import CamelModel

from app.settings import Settings

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
        self.logger = Logger()
        settings = Settings()
        db = boto3.resource('dynamodb')
        self.table = db.Table(f'{settings.app_stage}-cache')

    @tracer.capture_method
    async def get_key_value_by_key(self, key: str) -> Optional[KeyValue]:
        self.logger.info(f'Get value for key={key}')
        response = self.table.query(KeyConditionExpression=Key('key').eq(key))
        if response['Count'] == 0:
            error_message = f'The requested value was not found for {key=}'
            self.logger.info(error_message)
            return None
        return KeyValue.parse_obj(response['Items'][0])

    @tracer.capture_method
    async def put_key_value(self, data: dict):
        expired_at = (
            pendulum.from_timestamp(data.get('ttl')) if data.get('ttl') else None
        )
        self.table.put_item(
            Item={
                'key': data['key'],
                'value': data['value'],
                'created_at': pendulum.now().to_iso8601_string(),
                'ttl': expired_at.int_timestamp if expired_at else None,
            }
        )
        self.logger.info(
            f'Value for key successfully stored until {expired_at=}, {data=}'
        )
