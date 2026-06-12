import json
import uuid
from typing import Any

import pendulum
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app import Settings

BASE_URL = "/api/cache"
HEADERS = {
    "X-Api-Key": pytest.cache_service_api_key_ssm_param_value,
}
ERROR_MESSAGE_MISSING_X_API_KEY = {"message": "Invalid or missing API key"}


class TestCacheApi:
    @pytest.fixture
    def test_client(self, initialize_cache_table, settings: Settings) -> TestClient:
        from app.api_handler import app

        return TestClient(
            app,
            raise_server_exceptions=True,
        )

    def test_fail_to_create_cache_due_to_empty_body(self, test_client: TestClient):
        response = test_client.post(
            BASE_URL,
            json={},
            headers=HEADERS,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_fail_to_create_cache_due_to_missing_x_api_key(
        self, data: dict[str, str], test_client: TestClient
    ):
        response = test_client.post(
            BASE_URL,
            json={"key": str(uuid.uuid4()), "value": json.dumps(data), "ttl": 3600},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == ERROR_MESSAGE_MISSING_X_API_KEY

    def test_successfully_create_cache(
        self, data: dict[str, str], test_client: TestClient
    ):
        response = test_client.post(
            BASE_URL,
            json={"key": str(uuid.uuid4()), "value": json.dumps(data), "ttl": 3600},
            headers=HEADERS,
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_fail_to_get_cache_due_to_invalid_key(self, test_client: TestClient):
        response = test_client.get(
            f"{BASE_URL}/{uuid.uuid4()}",
            headers=HEADERS,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        json_body = response.json()
        assert json_body["status"] == status.HTTP_404_NOT_FOUND
        assert json_body["message"] == "KeyValue was not found"

    def test_fail_to_get_cache_due_to_missing_x_api_key(self, test_client: TestClient):
        response = test_client.get(
            f"{BASE_URL}/{uuid.uuid4()}",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == ERROR_MESSAGE_MISSING_X_API_KEY

    def test_successfully_get_cache(
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

    def test_successfully_get_token_cache(
        self, token_data: dict[str, Any], test_client: TestClient
    ):
        response = test_client.get(
            f"{BASE_URL}/{token_data['key']}",
            headers=HEADERS,
        )

        assert response.status_code == status.HTTP_200_OK

        json_body = response.json()
        assert token_data["key"] == json_body["key"]

        for k, v in token_data["value"].items():
            assert str(v) if v else v == json_body["value"].get(k)
        assert token_data["created_at"] == json_body["createdAt"]
        assert token_data["ttl"] == json_body["ttl"]

    def test_successfully_health_check(self, test_client: TestClient):
        response = test_client.get("/health", headers=HEADERS)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "healthy"}

    def test_successfully_create_cache_without_ttl(self, test_client: TestClient):
        response = test_client.post(
            BASE_URL,
            json={"key": str(uuid.uuid4()), "value": "no-ttl-value"},
            headers=HEADERS,
        )

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.parametrize(
        "invalid_ttl",
        [
            pytest.param(0, id="ttl_zero"),
            pytest.param(-1, id="ttl_negative"),
            pytest.param("abc", id="ttl_string"),
        ],
    )
    def test_fail_to_create_cache_due_to_invalid_ttl(
        self, test_client: TestClient, invalid_ttl
    ):
        response = test_client.post(
            BASE_URL,
            json={
                "key": str(uuid.uuid4()),
                "value": "some-value",
                "ttl": invalid_ttl,
            },
            headers=HEADERS,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        json_body = response.json()

        assert json_body["status"] == status.HTTP_400_BAD_REQUEST
        assert json_body["message"] == "Validation Error"
        assert "id" in json_body
        assert "errors" in json_body
        assert isinstance(json_body["errors"], list)
        assert len(json_body["errors"]) > 0

    def test_fail_to_create_cache_due_to_missing_key(self, test_client: TestClient):
        response = test_client.post(
            BASE_URL,
            json={"value": "some-value"},
            headers=HEADERS,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        json_body = response.json()
        assert json_body["status"] == status.HTTP_400_BAD_REQUEST
        assert json_body["message"] == "Validation Error"
        assert "id" in json_body
        assert "errors" in json_body
        assert any("key" in str(e.get("loc", [])) for e in json_body["errors"])

    def test_fail_to_create_cache_due_to_missing_value(self, test_client: TestClient):
        response = test_client.post(
            BASE_URL,
            json={"key": "some-key"},
            headers=HEADERS,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        json_body = response.json()
        assert json_body["status"] == status.HTTP_400_BAD_REQUEST
        assert json_body["message"] == "Validation Error"
        assert "id" in json_body
        assert "errors" in json_body
        assert any("value" in str(e.get("loc", [])) for e in json_body["errors"])

    def test_successfully_get_cache_has_expired_at_field(
        self, data: dict[str, str], test_client: TestClient
    ):
        response = test_client.get(
            f"{BASE_URL}/{data['key']}",
            headers=HEADERS,
        )

        assert response.status_code == status.HTTP_200_OK

        json_body = response.json()
        assert "expiredAt" in json_body

        expected_expired_at = pendulum.from_timestamp(data["ttl"]).to_iso8601_string()
        assert json_body["expiredAt"] == expected_expired_at

    def test_successfully_get_cache_has_correlation_id_header(
        self, data: dict[str, str], test_client: TestClient
    ):
        response = test_client.get(
            f"{BASE_URL}/{data['key']}",
            headers=HEADERS,
        )

        assert response.status_code == status.HTTP_200_OK

        assert "X-Correlation-ID" in response.headers
        correlation_id = response.headers["X-Correlation-ID"]
        assert correlation_id is not None
        assert len(correlation_id) > 0
        # Verify it's a valid UUID
        uuid.UUID(correlation_id)

    def test_successfully_get_cache_has_cors_headers(
        self, data: dict[str, str], test_client: TestClient
    ):
        cors_headers = {**HEADERS, "Origin": "https://example.com"}
        response = test_client.get(
            f"{BASE_URL}/{data['key']}",
            headers=cors_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers.get("access-control-allow-origin") == "*"

    def test_successfully_preflight_cors_request(self, test_client: TestClient):
        cors_headers = {
            **HEADERS,
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type,x-api-key",
        }
        response = test_client.options(
            BASE_URL,
            headers=cors_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers.get("access-control-allow-origin") == "*"

        allow_methods = response.headers.get("access-control-allow-methods", "")
        assert "GET" in allow_methods
        assert "POST" in allow_methods

        allow_headers = response.headers.get("access-control-allow-headers", "")
        assert "content-type" in allow_headers.lower()
        assert "x-api-key" in allow_headers.lower()

    def test_fail_to_get_cache_returns_error_response_shape(
        self, test_client: TestClient
    ):
        response = test_client.get(
            f"{BASE_URL}/{uuid.uuid4()}",
            headers=HEADERS,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        json_body = response.json()
        assert "status" in json_body
        assert "id" in json_body
        assert "message" in json_body
        assert json_body["status"] == status.HTTP_404_NOT_FOUND
        assert json_body["message"] == "KeyValue was not found"
        uuid.UUID(json_body["id"])

    def test_fail_to_create_cache_returns_validation_error_response_shape(
        self, test_client: TestClient
    ):
        response = test_client.post(
            BASE_URL,
            json={},
            headers=HEADERS,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        json_body = response.json()
        assert "status" in json_body
        assert "id" in json_body
        assert "message" in json_body
        assert "errors" in json_body
        assert json_body["status"] == status.HTTP_400_BAD_REQUEST
        assert json_body["message"] == "Validation Error"
        assert isinstance(json_body["errors"], list)
        assert len(json_body["errors"]) > 0
        uuid.UUID(json_body["id"])

    def test_botocore_error_handler_returns_error_response_shape(
        self, test_client: TestClient
    ):
        """Directly invoke botocore_error_handler and verify ErrorResponse shape."""
        import json as _json

        from fastapi import Request

        from app.api_handler import botocore_error_handler

        request = Request(
            scope={
                "type": "http",
                "method": "GET",
                "path": "/api/cache/test-key",
                "headers": [],
                "query_string": b"",
                "server": ("test", 80),
            }
        )
        error = Exception("Simulated DynamoDB failure")

        response = botocore_error_handler(request, error)
        json_body = _json.loads(response.body)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "status" in json_body
        assert "id" in json_body
        assert "message" in json_body
        assert json_body["status"] == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Exception" in json_body["message"]
        uuid.UUID(json_body["id"])

    def test_botocore_error_handler_returns_error_response_for_botocore_error(
        self, test_client: TestClient
    ):
        import json as _json

        from botocore.exceptions import BotoCoreError
        from fastapi import Request

        from app.api_handler import botocore_error_handler

        request = Request(
            scope={
                "type": "http",
                "method": "POST",
                "path": "/api/cache",
                "headers": [],
                "query_string": b"",
                "server": ("test", 80),
            }
        )

        class FakeConnectionError(BotoCoreError):
            pass

        error = FakeConnectionError()

        response = botocore_error_handler(request, error)
        json_body = _json.loads(response.body)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "status" in json_body
        assert "id" in json_body
        assert "message" in json_body
        assert json_body["status"] == status.HTTP_500_INTERNAL_SERVER_ERROR
        uuid.UUID(json_body["id"])
