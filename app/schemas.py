from typing import Any

from pydantic import conint

from app.services import CamelModel


class CreateKeyValue(CamelModel):
    key: str
    value: Any
    ttl: conint(gt=0) | None = None
