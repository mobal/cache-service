import pytest

from app.services import CacheService


@pytest.fixture
def cache_service() -> CacheService:
    return CacheService()
