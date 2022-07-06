import uuid

import pendulum
import pytest
from boto3.dynamodb.conditions import Key, Attr

from app.services import CacheService


@pytest.mark.asyncio
class TestCacheService:

    @pytest.fixture
    def cache_service(self, init_db) -> CacheService:
        return CacheService()

    @pytest.fixture
    def data(self) -> dict:
        return {
            'key': str(
                uuid.uuid4()),
            'value': 'Some random value',
            'ttl': 3600}

    @pytest.fixture
    def init_db(self, config, data, dynamodb_client) -> None:
        table_name = f'{config.app_stage}-cache'
        dynamodb_client.create_table(TableName=table_name,
                                     KeySchema=[{'AttributeName': 'key',
                                                 'KeyType': 'HASH'}],
                                     AttributeDefinitions=[{'AttributeName': 'key',
                                                            'AttributeType': 'S'}],
                                     ProvisionedThroughput={'ReadCapacityUnits': 1,
                                                            'WriteCapacityUnits': 1})
        table = dynamodb_client.Table(table_name)
        table.put_item(
            Item={
                'key': data['key'],
                'value': data['value'],
                'expired_at': pendulum.now().add(hours=1).to_iso8601_string()})

    @pytest.fixture
    def table(self, config, dynamodb_client):
        return dynamodb_client.Table(f'{config.app_stage}-cache')

    async def test_fail_to_get_key_value_with_invalid_uuid(self, cache_service):
        result = await cache_service.get_key_value_by_key(str(uuid.uuid4()))
        assert result is None

    async def test_successfully_get_key_value(self, cache_service, data):
        result = await cache_service.get_key_value_by_key(data['key'])
        assert data['key'] == result.key
        assert data['value'] == result.value

    async def test_successfully_put_key_value(self, cache_service, data, table):
        await cache_service.put_key_value(data)
        result = table.query(
            KeyConditionExpression=Key('key').eq(
                data['key']), FilterExpression=Attr('expired_at').gte(
                pendulum.now().to_iso8601_string()))
        assert 1 == result['Count']
        item = result['Items'][0]
        assert data['key'] == item['key']

    async def test_successfully_put_key_value_with_short_ttl(self, cache_service, data, table):
        now = pendulum.now()
        await cache_service.put_key_value(data)
        result = table.query(
            KeyConditionExpression=Key('key').eq(
                data['key']), FilterExpression=Attr('expired_at').gte(
                pendulum.now().to_iso8601_string()))
        assert 1 == result['Count']
        item = result['Items'][0]
        assert data['key'] == item['key']
        # Get datetime as int timestamp to deal with milliseconds
        assert now.add(
            seconds=data['ttl']).int_timestamp == pendulum.parse(
            item['expired_at']).int_timestamp
