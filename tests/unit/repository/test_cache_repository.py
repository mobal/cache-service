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
