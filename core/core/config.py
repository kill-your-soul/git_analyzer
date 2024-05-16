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
    CELERY_BROKER: str
    CELERY_BACKEND: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = ""


settings = Settings()
