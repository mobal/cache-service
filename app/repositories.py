from typing import Any

import boto3
from aws_lambda_powertools import Logger

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

    async def get_key_value_by_key(self, key: str) -> dict[str, Any] | None:
        response = self._table.get_item(Key={"key": key})
        return response.get("Item", None)
