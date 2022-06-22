import pytest
from fastapi import HTTPException
from starlette import status


@pytest.fixture
def key_value_dict() -> dict:
    return {'key': '591eecfb-887a-4dc3-a401-c15af829f1b2', 'value': 'asd',
            'expired_at': '2022-06-20T23:25:59.308688+02:00'}


@pytest.mark.asyncio
async def test_successfully_get_cache_value(mocker, key_value_dict, test_client, cache_service) -> None:
    mocker.patch('app.services.CacheService.get_key_value_by_key', return_value=key_value_dict)
    response = test_client.get(f'/api/cache/{key_value_dict["key"]}')
    assert status.HTTP_200_OK == response.status_code
    result = response.json()
    assert key_value_dict['key'] == result['key']
    assert key_value_dict['value'] == result['value']
    assert key_value_dict['expired_at'] == result['expired_at']
    cache_service.get_key_value_by_key.assert_called_once_with(key_value_dict['key'])


@pytest.mark.asyncio
async def test_fail_to_get_cache_value(mocker, key_value_dict, test_client, cache_service) -> None:
    mocker.patch('app.services.CacheService.get_key_value_by_key', side_effect=HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail='err'))
    response = test_client.get(f'/api/cache/{key_value_dict["key"]}')
    assert status.HTTP_404_NOT_FOUND == response.status_code
    result = response.json()
    assert status.HTTP_404_NOT_FOUND == result['status']
    assert 'err' == result['message']
    cache_service.get_key_value_by_key.assert_called_once_with(key_value_dict['key'])


@pytest.mark.asyncio
async def test_successfully_put_value(mocker, key_value_dict, test_client, cache_service) -> None:
    mocker.patch('app.services.CacheService.put_key_value', return_value=None)
    request_body = {'key': '591eecfb-887a-4dc3-a401-c15af829f1b2', 'value': 'asd', 'ttl': 0}
    response = test_client.post('/api/cache', json=request_body)
    assert status.HTTP_201_CREATED == response.status_code
    cache_service.put_key_value.assert_called_once_with(request_body)


@pytest.mark.asyncio
async def test_fail_to_put_value_because_body_is_empty(key_value_dict, test_client) -> None:
    response = test_client.post('/api/cache', json='')
    assert status.HTTP_400_BAD_REQUEST == response.status_code


@pytest.mark.asyncio
async def test_fail_to_put_value_because_body_is_none(key_value_dict, test_client) -> None:
    response = test_client.post('/api/cache', json=None)
    assert status.HTTP_400_BAD_REQUEST == response.status_code


@pytest.mark.asyncio
async def test_fail_to_put_value_because_body_is_invalid(key_value_dict, test_client) -> None:
    response = test_client.post('/api/cache', json='{"key": "","value": "","ttl": 0}')
    assert status.HTTP_400_BAD_REQUEST == response.status_code
