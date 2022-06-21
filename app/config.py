from pydantic import BaseSettings


class Configuration(BaseSettings):
    app_name: str
    app_stage: str
    app_timezone: str

    class Config:
        env_file = '.env'
