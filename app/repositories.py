from typing import Any

import boto3
from aws_lambda_powertools import Logger

from app import settings

logger = Logger(utc=True)


class CacheRepository:
    def __init__(self):
        self._table = (
            boto3.Session().resource("dynamodb").Table(f"{settings.stage}-cache")
        )

    def create_key_value(self, data: dict):
        self._table.put_item(Item=data)

    def get_key_value_by_key(self, key: str) -> dict[str, Any] | None:
        response = self._table.get_item(Key={"key": key})
        return response.get("Item", None)
