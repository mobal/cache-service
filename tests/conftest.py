import boto3
import pytest
from moto import mock_dynamodb
from starlette.testclient import TestClient

from app.config import Configuration
from app.main import app


@pytest.fixture
def config():
    return Configuration()


@pytest.fixture
def dynamodb_client():
    with mock_dynamodb():
        yield boto3.resource('dynamodb')


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)
