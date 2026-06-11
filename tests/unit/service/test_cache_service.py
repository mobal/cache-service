import pytest
from fastapi import status
from pytest_mock import MockerFixture

from app.exceptions import KeyValueNotFoundException
from app.repositories import CacheRepository
from app.services import CacheService


class TestCacheService:
    def test_fail_to_get_non_existent_key(
        self,
        mocker: MockerFixture,
        data: dict,
    ):
        repository_mock = mocker.Mock(spec=CacheRepository)
        repository_mock.get_key_value_by_key.return_value = None
        service = CacheService(repository=repository_mock)

        with pytest.raises(KeyValueNotFoundException) as excinfo:
            service.get_key_value_by_key(data["key"])

        assert KeyValueNotFoundException.__name__ == excinfo.typename
        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert "KeyValue was not found" == excinfo.value.detail
        repository_mock.get_key_value_by_key.assert_called_once_with(data["key"])

    def test_successfully_get_key_value(
        self,
        mocker: MockerFixture,
        data: dict,
    ):
        repository_mock = mocker.Mock(spec=CacheRepository)
        repository_mock.get_key_value_by_key.return_value = data
        service = CacheService(repository=repository_mock)

        result = service.get_key_value_by_key(data["key"])

        assert data["key"] == result.key
        assert data["value"] == result.value
        assert data["created_at"] == result.created_at
        repository_mock.get_key_value_by_key.assert_called_once_with(data["key"])

    def test_successfully_create_key_value(
        self,
        mocker: MockerFixture,
        data: dict,
    ):
        repository_mock = mocker.Mock(spec=CacheRepository)
        service = CacheService(repository=repository_mock)

        service.create_key_value(data)

        repository_mock.create_key_value.assert_called_once_with(data)

    def test_successfully_create_key_value_without_ttl(
        self,
        mocker: MockerFixture,
        data: dict,
    ):
        del data["ttl"]
        repository_mock = mocker.Mock(spec=CacheRepository)
        service = CacheService(repository=repository_mock)

        service.create_key_value(data)

        repository_mock.create_key_value.assert_called_once_with(data)
