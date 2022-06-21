import uuid

import pendulum
import pytest
from boto3.dynamodb.conditions import Key, Attr
from fastapi import HTTPException

from app.services import CacheService


@pytest.mark.asyncio
class TestCacheService:
    @pytest.fixture
    def init_db(self, config, data_dict, dynamodb_client) -> None:
        table_name = f'{config.app_stage}-cache'
        dynamodb_client.create_table(TableName=table_name,
                                     KeySchema=[{'AttributeName': 'key', 'KeyType': 'HASH'}],
                                     AttributeDefinitions=[{'AttributeName': 'key', 'AttributeType': 'S'}],
                                     ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1})
        table = dynamodb_client.Table(table_name)
        table.put_item(Item={'key': data_dict['key'], 'value': data_dict['value'],
                             'expired_at': '9999-12-31T23:59:59Z'})

    @pytest.fixture
    def cache_service(self, init_db) -> CacheService:
        return CacheService()

    @pytest.fixture
    def table(self, config, dynamodb_client):
        return dynamodb_client.Table(f'{config.app_stage}-cache')

    async def test_fail_to_get_key_value_with_invalid_uuid(self, cache_service):
        random_uuid = uuid.uuid4()
        with pytest.raises(HTTPException) as err:
            await cache_service.get_key_value_by_key(str(random_uuid))
        assert err.typename == 'HTTPException'
        assert (str(random_uuid) in err.value.detail) is True

    async def test_successfully_get_key_value(self, cache_service, data_dict):
        result = await cache_service.get_key_value_by_key(data_dict['key'])
        assert data_dict['key'] == result['key']
        assert data_dict['value'] == result['value']
        assert pendulum.datetime(9999, 12, 31, 23, 59, 59).to_iso8601_string() == result['expired_at']

    async def test_successfully_put_key_value(self, cache_service, data_dict, table):
        await cache_service.put_key_value(data_dict)
        result = table.query(
            KeyConditionExpression=Key('key').eq(data_dict['key']),
            FilterExpression=Attr('expired_at').gte(pendulum.now().to_iso8601_string())
        )
        assert 1 == result['Count']
        item = result['Items'][0]
        assert data_dict['key'] == item['key']

    async def test_successfully_put_key_value_with_short_ttl(self, cache_service, data_dict, table):
        data_dict['ttl'] = 3600
        now = pendulum.now()
        await cache_service.put_key_value(data_dict)
        result = table.query(
            KeyConditionExpression=Key('key').eq(data_dict['key']),
            FilterExpression=Attr('expired_at').gte(pendulum.now().to_iso8601_string())
        )
        assert 1 == result['Count']
        item = result['Items'][0]
        assert data_dict['key'] == item['key']
        assert now.add(seconds=data_dict['ttl']).int_timestamp == pendulum.parse(item['expired_at']).int_timestamp
