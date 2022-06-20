import uuid

import boto3
import pendulum
import pytest
from boto3.dynamodb.conditions import Key, Attr
from fastapi import HTTPException
from moto import mock_dynamodb

from app.config import Configuration
from app.services import CacheService


@pytest.mark.asyncio
class TestCacheService:
    cache_service = CacheService()
    config = Configuration()

    @pytest.fixture
    def data_dict(self) -> dict:
        return {'key': str(uuid.uuid4()), 'value': 'value', 'ttl': 0}

    @pytest.fixture
    def setup_dynamodb(self) -> None:
        self.key_value = {'key': str(uuid.uuid4()), 'value': 'value', 'ttl': 100}
        session = boto3.Session()
        db = session.resource('dynamodb')
        self.table = db.Table(f'{self.config.app_stage}-cache')
        self.table.put_item(Item={'key': self.key_value['key'], 'value': self.key_value['value'],
                                  'expired_at': pendulum.datetime(9999, 12, 31, 23, 59, 59).to_iso8601_string()})

    @mock_dynamodb
    async def test_fail_to_get_key_value_with_invalid_uuid(self, setup_dynamodb):
        random_uuid = uuid.uuid4()
        with pytest.raises(HTTPException) as err:
            await self.cache_service.get_key_value_by_key(str(random_uuid))
        assert err.typename == 'HTTPException'
        assert (str(random_uuid) in err.value.detail) is True

    async def test_successfully_get_key_value(self, setup_dynamodb):
        result = await self.cache_service.get_key_value_by_key(self.key_value['key'])
        assert self.key_value['key'] == result['key']
        assert self.key_value['value'] == result['value']
        assert pendulum.datetime(9999, 12, 31, 23, 59, 59).to_iso8601_string() == result['expired_at']

    @mock_dynamodb
    async def test_successfully_put_key_value(self, setup_dynamodb, data_dict):
        await self.cache_service.put_key_value(data_dict)
        result = self.table.query(
            KeyConditionExpression=Key('key').eq(data_dict['key']),
            FilterExpression=Attr('expired_at').gte(pendulum.now().to_iso8601_string())
        )
        assert 1 == result['Count']
        item = result['Items'][0]
        assert data_dict['key'] == item['key']

    @mock_dynamodb
    async def test_successfully_put_key_value_with_short_ttl(self, setup_dynamodb, data_dict):
        data_dict['ttl'] = 3600
        now = pendulum.now()
        await self.cache_service.put_key_value(data_dict)
        result = self.table.query(
            KeyConditionExpression=Key('key').eq(data_dict['key']),
            FilterExpression=Attr('expired_at').gte(pendulum.now().to_iso8601_string())
        )
        assert 1 == result['Count']
        item = result['Items'][0]
        assert data_dict['key'] == item['key']
        assert now.add(seconds=data_dict['ttl']).int_timestamp == pendulum.parse(item['expired_at']).int_timestamp
