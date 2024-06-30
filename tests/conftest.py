import uuid

import boto3
import pendulum
import pytest
from moto import mock_aws

from app.settings import Settings


def pytest_configure():
    pytest.service_name = "cache-service"
    pytest.table_name = "test-cache"


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def data() -> dict:
    return {
        "key": str(uuid.uuid4()),
        "value": "Some random value",
        "created_at": pendulum.now().to_iso8601_string(),
        "ttl": pendulum.now().int_timestamp,
    }


@pytest.fixture
def dynamodb_resource(settings: Settings):
    with mock_aws():
        yield boto3.Session().resource(
            "dynamodb",
            region_name="eu-central-1",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )


@pytest.fixture
def initialize_cache_table(data: dict, dynamodb_resource, cache_table):
    dynamodb_resource.create_table(
        TableName=pytest.table_name,
        KeySchema=[{"AttributeName": "key", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "key", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    cache_table.put_item(
        Item={
            "key": data["key"],
            "value": data["value"],
            "created_at": data["created_at"],
            "ttl": data["ttl"],
        }
    )


@pytest.fixture
def cache_table(dynamodb_resource):
    return dynamodb_resource.Table(pytest.table_name)
