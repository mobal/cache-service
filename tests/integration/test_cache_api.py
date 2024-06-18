import json
import uuid

import pytest
from starlette import status
from starlette.testclient import TestClient


@pytest.mark.asyncio
class TestCacheApi:
    BASE_URL = "/api/cache"

    @pytest.fixture
    def test_client(self, initialize_cache_table) -> TestClient:
        from app.main import app

        return TestClient(app, raise_server_exceptions=False)

    async def test_fail_to_create_cache_due_to_empty_body(
        self, test_client: TestClient
    ):
        response = test_client.post(
            self.BASE_URL,
            json={},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_successfully_create_cache(
        self, data: dict[str, str], test_client: TestClient
    ):
        response = test_client.post(
            self.BASE_URL,
            json={"key": str(uuid.uuid4()), "value": json.dumps(data), "ttl": 3600},
        )

        assert response.status_code == status.HTTP_201_CREATED

    async def test_fail_to_get_cache_due_to_invalid_key(self, test_client: TestClient):
        response = test_client.get(f"{self.BASE_URL}/{uuid.uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        json = response.json()
        assert json["status"] == status.HTTP_404_NOT_FOUND
        assert json["message"] == "KeyValue was not found"

    async def test_successfully_get_cache(
        self, data: dict[str, str], test_client: TestClient
    ):
        response = test_client.get(f"{self.BASE_URL}/{data['key']}")

        assert response.status_code == status.HTTP_200_OK
        json = response.json()
        assert data["key"] == json["key"]
        assert data["value"] == json["value"]
        assert data["created_at"] == json["createdAt"]
        assert data["ttl"] == json["ttl"]
