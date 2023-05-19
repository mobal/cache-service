import os
import pytest

from app.services import CacheService
from app.settings import Settings


def pytest_configure():
    pytest.service_name = 'cache-service'


def pytest_sessionstart():
    os.environ['DEBUG'] = 'true'

    os.environ['APP_NAME'] = pytest.service_name
    os.environ['APP_STAGE'] = 'test'
    os.environ['APP_TIMEZONE'] = 'Europe/Budapest'

    os.environ['AWS_REGION_NAME'] = 'eu-central-1'
    os.environ['AWS_ACCESS_KEY_ID'] = 'aws_access_key_id'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'aws_secret_access_key'

    os.environ['LOG_LEVEL'] = 'DEBUG'
    os.environ['POWERTOOLS_LOGGER_LOG_EVENT'] = 'true'
    os.environ['POWERTOOLS_METRICS_NAMESPACE'] = 'cache'
    os.environ['POWERTOOLS_SERVICE_NAME'] = pytest.service_name


@pytest.fixture
def cache_service() -> CacheService:
    return CacheService()


@pytest.fixture
def settings() -> Settings:
    return Settings()
