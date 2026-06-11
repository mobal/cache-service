import pytest
from fastapi import status
from pydantic import ValidationError
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

    def test_fail_to_get_key_value_due_to_repository_exception(
        self,
        mocker: MockerFixture,
        data: dict,
    ):
        repository_mock = mocker.Mock(spec=CacheRepository)
        repository_mock.get_key_value_by_key.side_effect = Exception(
            "DynamoDB connection error"
        )
        service = CacheService(repository=repository_mock)

        with pytest.raises(Exception) as excinfo:
            service.get_key_value_by_key(data["key"])

        assert "DynamoDB connection error" == str(excinfo.value)
        repository_mock.get_key_value_by_key.assert_called_once_with(data["key"])

    def test_fail_to_get_key_value_due_to_missing_created_at_field(
        self,
        mocker: MockerFixture,
        data: dict,
    ):
        repository_mock = mocker.Mock(spec=CacheRepository)
        bad_data = {k: v for k, v in data.items() if k != "created_at"}
        repository_mock.get_key_value_by_key.return_value = bad_data
        service = CacheService(repository=repository_mock)

        with pytest.raises(ValidationError) as excinfo:
            service.get_key_value_by_key(data["key"])

        errors = excinfo.value.errors()
        assert any("createdAt" in str(e.get("loc", ())) for e in errors)
        repository_mock.get_key_value_by_key.assert_called_once_with(data["key"])

    def test_successfully_get_key_value_with_extra_fields(
        self,
        mocker: MockerFixture,
        data: dict,
    ):
        repository_mock = mocker.Mock(spec=CacheRepository)
        extra_data = {**data, "extra_field": "should_be_ignored"}
        repository_mock.get_key_value_by_key.return_value = extra_data
        service = CacheService(repository=repository_mock)

        result = service.get_key_value_by_key(data["key"])

        assert data["key"] == result.key
        assert data["value"] == result.value
        assert data["created_at"] == result.created_at
        assert not hasattr(result, "extra_field")
        repository_mock.get_key_value_by_key.assert_called_once_with(data["key"])

    def test_create_key_value_mutates_input_dict(
        self,
        mocker: MockerFixture,
        data: dict,
    ):
        repository_mock = mocker.Mock(spec=CacheRepository)
        service = CacheService(repository=repository_mock)
        input_copy = dict(data)

        service.create_key_value(data)

        assert "created_at" in data
        assert data["created_at"] is not None
        assert data["ttl"] is not None
        assert data["created_at"] != input_copy.get("created_at") or data[
            "ttl"
        ] != input_copy.get("ttl")
        repository_mock.create_key_value.assert_called_once()

    def test_successfully_create_key_value_with_empty_key(
        self,
        mocker: MockerFixture,
        data: dict,
    ):
        repository_mock = mocker.Mock(spec=CacheRepository)
        service = CacheService(repository=repository_mock)
        data["key"] = ""

        service.create_key_value(data)

        repository_mock.create_key_value.assert_called_once_with(data)
        assert data["created_at"] is not None

    def test_successfully_create_key_value_with_ttl_zero(
        self,
        mocker: MockerFixture,
        data: dict,
    ):
        repository_mock = mocker.Mock(spec=CacheRepository)
        service = CacheService(repository=repository_mock)
        data["ttl"] = 0

        service.create_key_value(data)

        assert data["ttl"] is None
        repository_mock.create_key_value.assert_called_once_with(data)

    def test_fail_to_create_key_value_due_to_repository_exception(
        self,
        mocker: MockerFixture,
        data: dict,
    ):
        repository_mock = mocker.Mock(spec=CacheRepository)
        repository_mock.create_key_value.side_effect = Exception("DynamoDB write error")
        service = CacheService(repository=repository_mock)

        with pytest.raises(Exception) as excinfo:
            service.create_key_value(data)

        assert "DynamoDB write error" == str(excinfo.value)
        repository_mock.create_key_value.assert_called_once()
