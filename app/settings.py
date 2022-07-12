from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str
    app_stage: str
    app_timezone: str
