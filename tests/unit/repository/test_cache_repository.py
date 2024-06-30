from typing import Any

import pytest

from app.repositories import CacheRepository


@pytest.mark.asyncio
class TestCacheRepository:
    @pytest.fixture
    def cache_repository(self, initialize_cache_table) -> CacheRepository:
        return CacheRepository()

    async def test_successfully_create_key_value(
        self, cache_repository: CacheRepository, cache_table, data: dict[str, Any]
    ):
        data["key"] = "test"
        data["value"] = "test"

        await cache_repository.create_key_value(data)

        response = cache_table.get_item(
            Key={"key": data["key"]},
        )

        assert response.get("Item", None)

        item = response["Item"]
        assert "test" == item["key"]
        assert "test" == item["value"]
        assert data["created_at"] == item["created_at"]
        assert data["ttl"] == item["ttl"]

    async def test_successfully_get_key_value_by_key(
        self, cache_repository: CacheRepository, data: dict[str, Any]
    ):
        assert data == await cache_repository.get_key_value_by_key(data["key"])

    async def test_fail_to_get_key_value_by_key(
        self, cache_repository: CacheRepository
    ):
        item = await cache_repository.get_key_value_by_key("asd")

        assert item is None
