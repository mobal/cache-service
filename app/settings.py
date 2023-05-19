from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str
    app_stage: str
    app_timezone: str
    aws_access_key_id: str
    aws_secret_access_key: str
    debug: bool
