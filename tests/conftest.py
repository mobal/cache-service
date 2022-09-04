import pytest

from app.services import CacheService
from app.settings import Settings


@pytest.fixture
def cache_service() -> CacheService:
    return CacheService()


@pytest.fixture(autouse=True)
def set_environment_variables(monkeypatch):
    monkeypatch.setenv('APP_DEBUG', 'true')
    monkeypatch.setenv('APP_NAME', 'cache-service')
    monkeypatch.setenv('APP_STAGE', 'test')
    monkeypatch.setenv('APP_TIMEZONE', 'Europe/Budapest')

    monkeypatch.setenv('AWS_REGION_NAME', 'eu-central-1')
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'aws_access_key_id')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'aws_secret_access_key')

    monkeypatch.setenv('LOG_LEVEL', 'DEBUG')
    monkeypatch.setenv('POWERTOOLS_LOGGER_LOG_EVENT', 'true')
    monkeypatch.setenv('POWERTOOLS_METRICS_NAMESPACE', 'cache')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'cache-service')


@pytest.fixture
def settings() -> Settings:
    return Settings()
