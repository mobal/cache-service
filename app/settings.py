import os

from aws_lambda_powertools.utilities import parameters
from pydantic import computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str
    default_timezone: str
    aws_access_key_id: str
    aws_secret_access_key: str
    debug: bool
    stage: str

    @computed_field
    @property
    def api_key(self) -> str:
        return parameters.get_parameter(
            os.environ.get("CACHE_SERVICE_API_KEY_SSM_PARAM_NAME"), decrypt=True
        )
