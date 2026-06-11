from fastapi import Depends

from app.repositories import CacheRepository
from app.services import CacheService


def get_cache_repository() -> CacheRepository:
    return CacheRepository()


def get_cache_service(repository=Depends(get_cache_repository)) -> CacheService:
    return CacheService(repository=repository)
