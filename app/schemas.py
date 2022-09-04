from typing import Optional, Any
from fastapi_camelcase import CamelModel
from pydantic import conint


class CreateKeyValue(CamelModel):
    key: str
    value: Any
    ttl: Optional[conint(gt=0)]
