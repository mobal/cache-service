from typing import Any

import pendulum
from aws_lambda_powertools import Logger
from pydantic import BaseModel, ConfigDict, computed_field
from pydantic.alias_generators import to_camel

from app.exceptions import KeyValueNotFoundException
from app.repositories import CacheRepository

logger = Logger(utc=True)


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class KeyValue(CamelModel):
    key: str
    value: Any
    created_at: str
    ttl: int | None

    @computed_field
    def expired_at(self) -> str | None:
        return (
            pendulum.from_timestamp(self.ttl).to_iso8601_string() if self.ttl else None
        )


class CacheService:
    def __init__(self):
        self._repository = CacheRepository()

    def get_key_value_by_key(self, key: str) -> KeyValue | None:
        logger.info(f"Get value for key={key}")
        item = self._repository.get_key_value_by_key(key)
        if item is None:
            logger.info(f"The requested value was not found for {key=}")
            raise KeyValueNotFoundException("KeyValue was not found")
        return KeyValue(**item)

    def create_key_value(self, create_dict: dict[str, Any]):
        expired_at = (
            pendulum.from_timestamp(create_dict["ttl"])
            if create_dict.get("ttl")
            else None
        )
        create_dict["created_at"] = pendulum.now().to_iso8601_string()
        create_dict["ttl"] = expired_at.int_timestamp if expired_at else None
        self._repository.create_key_value(create_dict)
        logger.info(
            f"Value for key successfully stored until expired_at={expired_at.to_iso8601_string() if expired_at else None}, {create_dict=}"
        )
