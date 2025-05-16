import pytest
from fastapi import status
from pytest_mock import MockerFixture

from app.exceptions import KeyValueNotFoundException
from app.repositories import CacheRepository
from app.services import CacheService


class TestCacheService:
    @pytest.fixture
    def cache_repository(self) -> CacheRepository:
        return CacheRepository()

    def test_fail_to_get_key_value_with_invalid_uuid(
        self,
        mocker: MockerFixture,
        cache_service: CacheService,
        cache_repository: CacheRepository,
        data: dict,
    ):
        mocker.patch.object(CacheRepository, "get_key_value_by_key", return_value=None)

        with pytest.raises(KeyValueNotFoundException) as excinfo:
            cache_service.get_key_value_by_key(data["key"])

        assert KeyValueNotFoundException.__name__ == excinfo.typename
        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert "KeyValue was not found" == excinfo.value.detail
        cache_repository.get_key_value_by_key.assert_called_once_with(data["key"])

    def test_successfully_get_key_value(
        self,
        mocker: MockerFixture,
        cache_service: CacheService,
        cache_repository: CacheRepository,
        data: dict,
    ):
        mocker.patch.object(CacheRepository, "get_key_value_by_key", return_value=data)

        result = cache_service.get_key_value_by_key(data["key"])

        assert data["key"] == result.key
        assert data["value"] == result.value
        assert data["created_at"] == result.created_at
        cache_repository.get_key_value_by_key.assert_called_once_with(data["key"])

    def test_successfully_create_key_value(
        self,
        mocker: MockerFixture,
        cache_service: CacheService,
        cache_repository: CacheRepository,
        data: dict,
    ):
        mocker.patch.object(CacheRepository, "create_key_value", return_value=None)

        cache_service.create_key_value(data)

        cache_repository.create_key_value.assert_called_once_with(data)

    def test_successfully_create_key_value_without_ttl(
        self,
        mocker: MockerFixture,
        cache_service: CacheService,
        cache_repository: CacheRepository,
        data: dict,
    ):
        del data["ttl"]
        mocker.patch.object(CacheRepository, "create_key_value", return_value=None)

        cache_service.create_key_value(data)

        cache_repository.create_key_value.assert_called_once_with(data)
