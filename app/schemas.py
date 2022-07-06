from fastapi_camelcase import CamelModel
from pydantic import conint


class CreateKeyValue(CamelModel):
    key: str
    value: str
    ttl: conint(gt=0)
