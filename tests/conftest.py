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
def data_dict() -> dict:
    return {'key': 'c999ac5b-59cd-4d2e-9fb2-ee37652976c7', 'value': 'asd',
            'ttl': 3600}


@pytest.fixture
def dynamodb_client():
    with mock_dynamodb():
        yield boto3.resource('dynamodb')


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)