import uuid
import pendulum

import pytest
from fastapi import HTTPException
from starlette import status

from app.services import CacheService

BASE_URL = '/api/cache'


@pytest.fixture
def body() -> dict:
    return {
        'key': str(uuid.uuid4()),
        'value': 'Some random value',
        'ttl': 3600}


@pytest.fixture
def cache_service() -> CacheService:
    return CacheService()


@pytest.fixture
def key_value_dict(body) -> dict:
    return {
        'key': body['key'],
        'value': body['value'],
        'expired_at': pendulum.now().add(
            seconds=body['ttl']).to_iso8601_string()}


@pytest.mark.asyncio
async def test_successfully_get_cache_value(mocker, key_value_dict, test_client, cache_service) -> None:
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
async def test_fail_to_get_cache_value(mocker, key_value_dict, test_client, cache_service) -> None:
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
async def test_successfully_put_value(mocker, cache_service, body, test_client) -> None:
    mocker.patch('app.services.CacheService.put_key_value', return_value=None)
    response = test_client.post(BASE_URL, json=body)
    assert status.HTTP_201_CREATED == response.status_code
    cache_service.put_key_value.assert_called_once_with(body)


@pytest.mark.asyncio
async def test_fail_to_put_value_because_body_is_empty(test_client) -> None:
    response = test_client.post(BASE_URL, json='')
    assert status.HTTP_400_BAD_REQUEST == response.status_code


@pytest.mark.asyncio
async def test_fail_to_put_value_because_body_is_none(test_client) -> None:
    response = test_client.post(BASE_URL, json=None)
    assert status.HTTP_400_BAD_REQUEST == response.status_code


@pytest.mark.asyncio
async def test_fail_to_put_value_because_body_is_invalid(test_client) -> None:
    invalid_body = {'key': '', 'value': '', 'ttl': 'ttl'}
    response = test_client.post(BASE_URL, json=invalid_body)
    assert status.HTTP_400_BAD_REQUEST == response.status_code
