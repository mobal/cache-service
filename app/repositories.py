import boto3
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Key

from app.exceptions import KeyValueNotFoundException
from app.settings import Settings


class CacheRepository:
    def __init__(self):
        self._logger = Logger()
        settings = Settings()
        session = boto3.Session()
        dynamodb = session.resource('dynamodb')
        self._table = dynamodb.Table(f'{settings.app_stage}-cache')

    async def create_key_value(self, data: dict):
        self._table.put_item(Item=data)

    async def get_key_value_by_key(self, key: str) -> dict:
        response = self._table.query(KeyConditionExpression=Key('key').eq(key))
        self._logger.debug(response)
        if response['Count'] == 1:
            return response['Items'][0]
        self._logger.info(f'The requested value was not found for {key=}')
        raise KeyValueNotFoundException('KeyValue was not found')
