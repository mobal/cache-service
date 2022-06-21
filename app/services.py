import logging

import boto3
import pendulum
from boto3.dynamodb.conditions import Key, Attr
from fastapi import HTTPException
from fastapi_camelcase import CamelModel
from starlette import status

from app.config import Configuration


class KeyValue(CamelModel):
    key: str
    value: str
    ttl: int


class CacheService:
    def __init__(self):
        self.logger = logging.getLogger()
        config = Configuration()
        db = boto3.resource('dynamodb')
        self.table = db.Table(f'{config.app_stage}-cache')

    async def get_key_value_by_key(self, key: str) -> dict:
        self.logger.info(f'Get value for key={key}')
        response = self.table.query(
            KeyConditionExpression=Key('key').eq(key),
            FilterExpression=Attr('expired_at').gte(pendulum.now().to_iso8601_string())
        )
        if response['Count'] == 0:
            error_message = f'The requested value was not found for key={key}'
            self.logger.info(error_message)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_message)
        return response['Items'][0]

    async def put_key_value(self, data: dict) -> None:
        expired_at = pendulum.datetime(9999, 12, 31, 23, 59, 59)
        if data['ttl'] != 0:
            expired_at = pendulum.now().add(seconds=data['ttl'])
        self.table.put_item(Item={'key': data['key'], 'value': data['value'],
                                  'expired_at': expired_at.to_iso8601_string()})
        self.logger.info(f'Value for key successfully stored until expired_at={expired_at}, data={data}')
