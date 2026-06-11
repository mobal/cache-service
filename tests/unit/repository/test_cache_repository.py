from typing import Any

import pytest

from app.repositories import CacheRepository


class TestCacheRepository:
    @pytest.fixture
    def cache_repository(self, initialize_cache_table) -> CacheRepository:
        return CacheRepository()

    def test_successfully_create_key_value(
        self, cache_repository: CacheRepository, cache_table, data: dict[str, Any]
    ):
        data["key"] = "test"
        data["value"] = "test"

        cache_repository.create_key_value(data)

        response = cache_table.get_item(
            Key={"key": data["key"]},
        )

        assert response.get("Item", None)

        item = response["Item"]
        assert "test" == item["key"]
        assert "test" == item["value"]
        assert data["created_at"] == item["created_at"]
        assert data["ttl"] == item["ttl"]

    def test_successfully_get_key_value_by_key(
        self, cache_repository: CacheRepository, data: dict[str, Any]
    ):
        assert data == cache_repository.get_key_value_by_key(data["key"])

    def test_fail_to_get_key_value_by_key(self, cache_repository: CacheRepository):
        item = cache_repository.get_key_value_by_key("asd")

        assert item is None

    def test_successfully_overwrite_existing_key(
        self, cache_repository: CacheRepository, cache_table, data: dict[str, Any]
    ):
        data["key"] = "overwrite-key"
        data["value"] = "original-value"

        cache_repository.create_key_value(data)

        data["value"] = "updated-value"
        cache_repository.create_key_value(data)

        response = cache_table.get_item(Key={"key": "overwrite-key"})

        item = response.get("Item")
        assert item is not None
        assert item["value"] == "updated-value"
        assert item["key"] == "overwrite-key"

    def test_fail_to_create_key_value_due_to_dynamodb_error(
        self, mocker, cache_repository: CacheRepository, data: dict[str, Any]
    ):
        mocker.patch.object(
            cache_repository._table,
            "put_item",
            side_effect=Exception("ProvisionedThroughputExceededException"),
        )

        with pytest.raises(Exception) as excinfo:
            cache_repository.create_key_value(data)

        assert "ProvisionedThroughputExceededException" in str(excinfo.value)

    def test_fail_to_get_key_value_due_to_dynamodb_error(
        self, mocker, cache_repository: CacheRepository, data: dict[str, Any]
    ):
        mocker.patch.object(
            cache_repository._table,
            "get_item",
            side_effect=Exception("ResourceNotFoundException"),
        )

        with pytest.raises(Exception) as excinfo:
            cache_repository.get_key_value_by_key(data["key"])

        assert "ResourceNotFoundException" in str(excinfo.value)

    def test_successfully_create_key_value_with_unicode_key(
        self, cache_repository: CacheRepository, cache_table, data: dict[str, Any]
    ):
        """Unicode/special characters in key."""
        data["key"] = "héllo-世界-🌍"
        data["value"] = "unicode value"

        cache_repository.create_key_value(data)

        response = cache_table.get_item(Key={"key": "héllo-世界-🌍"})
        assert response.get("Item", None)
        assert response["Item"]["key"] == "héllo-世界-🌍"
        assert response["Item"]["value"] == "unicode value"

    @pytest.mark.parametrize(
        "empty_value, expected",
        [
            pytest.param("", "", id="empty_string"),
            pytest.param(None, None, id="none"),
            pytest.param({}, {}, id="empty_dict"),
        ],
    )
    def test_successfully_create_key_value_with_empty_value(
        self,
        cache_repository: CacheRepository,
        cache_table,
        data: dict[str, Any],
        empty_value,
        expected,
    ):
        data["key"] = f"empty-value-{type(empty_value).__name__}"
        data["value"] = empty_value

        cache_repository.create_key_value(data)

        response = cache_table.get_item(Key={"key": data["key"]})
        assert response.get("Item", None)
        assert response["Item"]["value"] == expected
