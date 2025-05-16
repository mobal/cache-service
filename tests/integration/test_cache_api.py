import json
import uuid
from typing import Any

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app import Settings

BASE_URL = "/api/cache"
HEADERS = {
    "X-Api-Key": pytest.cache_service_api_key_ssm_param_value,
}
ERROR_MESSAGE_MISSING_X_API_KEY = {"message": "Invalid or missing API key"}


@pytest.mark.asyncio
class TestCacheApi:
    @pytest.fixture
    def test_client(self, initialize_cache_table, settings: Settings) -> TestClient:
        from app.main import app

        return TestClient(
            app,
            raise_server_exceptions=True,
        )

    async def test_fail_to_create_cache_due_to_empty_body(
        self, test_client: TestClient
    ):
        response = test_client.post(
            BASE_URL,
            json={},
            headers=HEADERS,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_fail_to_create_cache_due_to_missing_x_api_key(
        self, data: dict[str, str], test_client: TestClient
    ):
        response = test_client.post(
            BASE_URL,
            json={"key": str(uuid.uuid4()), "value": json.dumps(data), "ttl": 3600},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == ERROR_MESSAGE_MISSING_X_API_KEY

    async def test_successfully_create_cache(
        self, data: dict[str, str], test_client: TestClient
    ):
        response = test_client.post(
            BASE_URL,
            json={"key": str(uuid.uuid4()), "value": json.dumps(data), "ttl": 3600},
            headers=HEADERS,
        )

        assert response.status_code == status.HTTP_201_CREATED

    async def test_fail_to_get_cache_due_to_invalid_key(self, test_client: TestClient):
        response = test_client.get(
            f"{BASE_URL}/{uuid.uuid4()}",
            headers=HEADERS,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        json_body = response.json()
        assert json_body["status"] == status.HTTP_404_NOT_FOUND
        assert json_body["message"] == "KeyValue was not found"

    async def test_fail_to_get_cache_due_to_missing_x_api_key(
        self, test_client: TestClient
    ):
        response = test_client.get(
            f"{BASE_URL}/{uuid.uuid4()}",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == ERROR_MESSAGE_MISSING_X_API_KEY

    async def test_successfully_get_cache(
        self, data: dict[str, str], test_client: TestClient
    ):
        response = test_client.get(
            f"{BASE_URL}/{data['key']}",
            headers=HEADERS,
        )

        assert response.status_code == status.HTTP_200_OK
        json_body = response.json()
        assert data["key"] == json_body["key"]
        assert data["value"] == json_body["value"]
        assert data["created_at"] == json_body["createdAt"]
        assert data["ttl"] == json_body["ttl"]

    async def test_successfully_get_token_cache(
        self, token_data: dict[str, Any], test_client: TestClient
    ):
        response = test_client.get(
            f"{BASE_URL}/{token_data['key']}",
            headers=HEADERS,
        )

        assert response.status_code == status.HTTP_200_OK

        json_body = response.json()
        assert token_data["key"] == json_body["key"]
        # Keep in mind, numbers retrieved from DynamoDB are stored as decimals, which are serialized to strings!
        for k, v in token_data["value"].items():
            assert str(v) if v else v == json_body["value"].get(k)
        assert token_data["created_at"] == json_body["createdAt"]
        assert token_data["ttl"] == json_body["ttl"]
