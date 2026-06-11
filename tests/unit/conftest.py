import pytest

from app.repositories import CacheRepository
from app.services import CacheService


@pytest.fixture
def cache_service() -> CacheService:
    return CacheService(repository=CacheRepository())
