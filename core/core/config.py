from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )
    PROJECT_NAME: str
    API_V1_STR: str = "/api/v1"
    VERSION: str
    TOKENS: list[str] = []
    # = Field(default_factory=lambda v: [x.strip() for x in v.split(",")])
    # @model_validator("TOKENS", mode="before")
    # def parse_tokens(value):
    #     return [token.strip() for token in value.split(",")]


settings = Settings()
