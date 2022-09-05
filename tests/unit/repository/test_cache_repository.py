import boto3
import pytest
from boto3.dynamodb.conditions import Key
from moto import mock_dynamodb
from starlette import status

from app.exceptions import KeyValueNotFoundException
from app.repositories import CacheRepository
from app.settings import Settings


@pytest.mark.asyncio
class TestCacheRepository:
    @pytest.fixture
    def cache_repository(self) -> CacheRepository:
        return CacheRepository()

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
                'created_at': data['created_at'],
                'ttl': data['ttl'],
            }
        )

    async def test_successfully_create_key_value(
        self, cache_repository: CacheRepository, data: dict, dynamodb_table
    ):
        data['key'] = 'test'
        data['value'] = 'test'
        await cache_repository.create_key_value(data)
        response = dynamodb_table.query(
            KeyConditionExpression=Key('id').eq(data['key']),
        )
        assert 1 == response['Count']
        item = response['Items'][0]
        assert 'test' == item['key']
        assert 'test' == item['value']
        assert data['created_at'] == item['created_at']
        assert data['ttl'] == item['ttl']

    async def test_successfully_get_key_value_by_key(
        self, cache_repository: CacheRepository, data: dict, dynamodb_table
    ):
        assert data == await cache_repository.get_key_value_by_key(data['key'])

    async def test_fail_to_get_key_value_by_key(
        self, cache_repository: CacheRepository
    ):
        item = await cache_repository.get_key_value_by_key('asd')
        assert item is None
