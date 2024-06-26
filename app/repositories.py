import boto3
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Key

from app.settings import Settings

logger = Logger(utc=True)
settings = Settings()


class CacheRepository:
    def __init__(self):
        self._table = (
            boto3.Session().resource("dynamodb").Table(f"{settings.stage}-cache")
        )

    async def create_key_value(self, data: dict):
        self._table.put_item(Item=data)

    async def get_key_value_by_key(self, key: str) -> dict[str, str] | None:
        response = self._table.query(KeyConditionExpression=Key("key").eq(key))
        if response["Count"] == 1:
            return response["Items"][0]
        return None
