import uuid

import boto3
import pendulum
import pytest
from boto3.dynamodb.conditions import Key, Attr
from moto import mock_dynamodb


@pytest.mark.asyncio
class TestCacheService:

    @pytest.fixture
    def data(self) -> dict:
        return {
            'key': str(
                uuid.uuid4()),
            'value': 'Some random value',
            'ttl': pendulum.now().int_timestamp}

    @pytest.fixture
    def dynamodb_resource(self):
        with mock_dynamodb():
            yield boto3.resource('dynamodb')

    @pytest.fixture
    def dynamodb_table(self, settings, dynamodb_resource):
        return dynamodb_resource.Table(f'{settings.app_stage}-cache')

    @pytest.fixture(autouse=True)
    def setup_table(
            self,
            settings,
            data,
            dynamodb_resource,
            dynamodb_table) -> None:
        table_name = f'{settings.app_stage}-cache'
        dynamodb_resource.create_table(TableName=table_name,
                                       KeySchema=[{'AttributeName': 'key',
                                                   'KeyType': 'HASH'}],
                                       AttributeDefinitions=[{'AttributeName': 'key',
                                                              'AttributeType': 'S'}],
                                       ProvisionedThroughput={'ReadCapacityUnits': 1,
                                                              'WriteCapacityUnits': 1})
        dynamodb_table.put_item(
            Item={
                'key': data['key'],
                'value': data['value'],
                'created_at': pendulum.now().to_iso8601_string(),
                'ttl': pendulum.now().add(hours=1).int_timestamp})

    async def test_fail_to_get_key_value_with_invalid_uuid(self, cache_service):
        result = await cache_service.get_key_value_by_key(str(uuid.uuid4()))
        assert result is None

    async def test_successfully_get_key_value(self, cache_service, data):
        result = await cache_service.get_key_value_by_key(data['key'])
        assert data['key'] == result.key
        assert data['value'] == result.value

    async def test_successfully_put_key_value(self, cache_service, data, dynamodb_table):
        await cache_service.put_key_value(data)
        result = dynamodb_table.query(
            KeyConditionExpression=Key('key').eq(
                data['key']), FilterExpression=Attr('expired_at').gte(
                pendulum.from_timestamp(data.get('ttl')).to_iso8601_string()))
        assert 1 == result['Count']
        item = result['Items'][0]
        assert data['key'] == item['key']
        assert data['value'] == item['value']
        assert data['ttl'] == item['ttl']
        assert item['created_at'] is not None
        assert pendulum.parse(
            item['expired_at']) == pendulum.from_timestamp(
            data['ttl'])

    async def test_successfully_put_key_value_without_ttl(self, cache_service, data, dynamodb_table):
        del data['ttl']
        await cache_service.put_key_value(data)
        result = dynamodb_table.query(
            KeyConditionExpression=Key('key').eq(
                data['key']), FilterExpression=Attr('expired_at').eq(None))
        assert 1 == result['Count']
        item = result['Items'][0]
        assert data['key'] == item['key']
        assert data['value'] == item['value']
        assert item['created_at'] is not None
        assert None is item['expired_at']
        assert None is item['ttl']
