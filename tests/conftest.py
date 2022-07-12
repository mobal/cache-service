import pytest

from app.services import CacheService
from app.settings import Settings


@pytest.fixture
def cache_service() -> CacheService:
    return CacheService()


@pytest.fixture(autouse=True)
def set_environment_variables(monkeypatch):
    monkeypatch.setenv('APP_NAME', 'cache-service')
    monkeypatch.setenv('APP_STAGE', 'test')
    monkeypatch.setenv('APP_TIMEZONE', 'Europe/Budapest')


@pytest.fixture
def settings():
    return Settings()
