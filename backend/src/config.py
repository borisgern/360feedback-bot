from typing import List

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

class GoogleSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GOOGLE_")

    SERVICE_ACCOUNT_KEY_PATH: str = "google_creds.json"
    SHEET_ID: str


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    host: str = "localhost"
    port: int = 6379
    db: int = 0

    @computed_field
    @property
    def dsn(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    BOT_TOKEN: str
    ADMIN_TELEGRAM_IDS: List[int] = Field(default_factory=list)
    redis: RedisSettings = RedisSettings()
    google: GoogleSettings = GoogleSettings()


settings = Settings()
