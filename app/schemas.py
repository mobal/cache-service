from typing import Any, Optional

from pydantic import conint

from app.services import CamelModel


class CreateKeyValue(CamelModel):
    key: str
    value: Any
    ttl: Optional[conint(gt=0)] = None
