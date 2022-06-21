from fastapi_camelcase import CamelModel


class CreateKeyValue(CamelModel):
    key: str
    value: str
    ttl: int
