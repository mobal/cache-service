from operator import inv
import uuid
import pendulum

import pytest
from fastapi import HTTPException
from starlette import status

from app.services import CacheService

BASE_URL = '/api/cache'


@pytest.fixture
def cache_service() -> CacheService:
    return CacheService()


@pytest.fixture
def key_value_body() -> dict:
    return {
        'key': str(uuid.uuid4()),
        'value': 'Some random value',
        'ttl': 3600}


@pytest.fixture
def key_value_dict(key_value_body) -> dict:
    return {
        'key': key_value_body['key'],
        'value': key_value_body['value'],
        'expired_at': pendulum.now().add(
            seconds=key_value_body['ttl']).to_iso8601_string()}


@pytest.mark.asyncio
async def test_successfully_get_key_value(mocker, key_value_dict, test_client, cache_service):
    mocker.patch(
        'app.services.CacheService.get_key_value_by_key',
        return_value=key_value_dict)
    response = test_client.get(f'{BASE_URL}/{key_value_dict["key"]}')
    assert status.HTTP_200_OK == response.status_code
    result = response.json()
    assert key_value_dict['key'] == result['key']
    assert key_value_dict['value'] == result['value']
    assert key_value_dict['expired_at'] == result['expired_at']
    cache_service.get_key_value_by_key.assert_called_once_with(
        key_value_dict['key'])


@pytest.mark.asyncio
async def test_fail_to_get_key_value(mocker, key_value_dict, test_client, cache_service):
    mocker.patch(
        'app.services.CacheService.get_key_value_by_key',
        side_effect=HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='err'))
    response = test_client.get(f'{BASE_URL}/{key_value_dict["key"]}')
    assert status.HTTP_404_NOT_FOUND == response.status_code
    result = response.json()
    assert status.HTTP_404_NOT_FOUND == result['status']
    assert 'err' == result['message']
    cache_service.get_key_value_by_key.assert_called_once_with(
        key_value_dict['key'])


@pytest.mark.asyncio
async def test_successfully_post_key_value(mocker, cache_service, key_value_body, test_client):
    mocker.patch('app.services.CacheService.put_key_value', return_value=None)
    response = test_client.post(BASE_URL, json=key_value_body)
    assert status.HTTP_201_CREATED == response.status_code
    cache_service.put_key_value.assert_called_once_with(key_value_body)


@pytest.mark.asyncio
async def test_fail_to_post_key_value_due_to_empty_body(test_client):
    response = test_client.post(BASE_URL, json='')
    assert status.HTTP_400_BAD_REQUEST == response.status_code


@pytest.mark.asyncio
async def test_fail_to_post_key_value_due_to_none_body(test_client):
    response = test_client.post(BASE_URL, json=None)
    assert status.HTTP_400_BAD_REQUEST == response.status_code


@pytest.mark.asyncio
async def test_fail_to_post_key_value_due_to_invalid_body(test_client):
    invalid_body = {'key': '', 'value': '', 'ttl': 'ttl'}
    response = test_client.post(BASE_URL, json=invalid_body)
    assert status.HTTP_400_BAD_REQUEST == response.status_code


@pytest.mark.asyncio
async def test_fail_to_post_key_value_due_to_invalid_ttl(test_client):
    invalid_body = {
        'key': 'jti',
        'value': 'a6e28bf9-942f-46a9-ac86-3c6dc3c8efb3',
        'ttl': 0}
    response = test_client.post(BASE_URL, json=invalid_body)
    assert status.HTTP_400_BAD_REQUEST == response.status_code
