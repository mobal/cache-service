import uuid

import boto3
import pendulum
import pytest
from boto3.dynamodb.conditions import Key
from moto import mock_dynamodb

from app.services import KeyValue, CacheService
from app.settings import Settings


@pytest.mark.asyncio
class TestCacheService:
    @pytest.fixture
    def data(self) -> dict:
        return {
            'key': str(uuid.uuid4()),
            'value': 'Some random value',
            'ttl': pendulum.now().int_timestamp,
        }

    @pytest.fixture
    def dynamodb_resource(self):
        with mock_dynamodb():
            yield boto3.resource('dynamodb')

    @pytest.fixture
    def dynamodb_table(self, settings, dynamodb_resource):
        return dynamodb_resource.Table(f'{settings.app_stage}-cache')

    @pytest.fixture(autouse=True)
    def setup_table(
        self, data: dict, dynamodb_resource, dynamodb_table, settings: Settings
    ):
        table_name = f'{settings.app_stage}-cache'
        dynamodb_resource.create_table(
            TableName=table_name,
            KeySchema=[{'AttributeName': 'key', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'key', 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1},
        )
        dynamodb_table.put_item(
            Item={
                'key': data['key'],
                'value': data['value'],
                'created_at': pendulum.now().to_iso8601_string(),
                'ttl': pendulum.now().add(hours=1).int_timestamp,
            }
        )

    async def test_fail_to_get_key_value_with_invalid_uuid(
        self, cache_service: CacheService
    ):
        result = await cache_service.get_key_value_by_key(str(uuid.uuid4()))
        assert result is None

    async def test_successfully_get_key_value(
        self, cache_service: CacheService, data: dict
    ):
        result = await cache_service.get_key_value_by_key(data['key'])
        assert data['key'] == result.key
        assert data['value'] == result.value

    async def test_successfully_put_key_value(
        self, cache_service: CacheService, data: dict, dynamodb_table
    ):
        await cache_service.put_key_value(data)
        result = dynamodb_table.query(KeyConditionExpression=Key('key').eq(data['key']))
        assert 1 == result['Count']
        item = result['Items'][0]
        assert data['key'] == item['key']
        assert data['value'] == item['value']
        assert data['ttl'] == item['ttl']
        assert item['created_at'] is not None
        key_value = KeyValue.parse_obj(item)
        assert (
            pendulum.from_timestamp(data['ttl']).to_iso8601_string()
            == key_value.expired_at
        )

    async def test_successfully_put_key_value_without_ttl(
        self, cache_service: CacheService, data: dict, dynamodb_table
    ):
        del data['ttl']
        await cache_service.put_key_value(data)
        result = dynamodb_table.query(KeyConditionExpression=Key('key').eq(data['key']))
        assert 1 == result['Count']
        item = result['Items'][0]
        assert data['key'] == item['key']
        assert data['value'] == item['value']
        assert item['created_at'] is not None
        assert None is item['ttl']
