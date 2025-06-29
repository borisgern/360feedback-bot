import json
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class GoogleSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GOOGLE_")

    SERVICE_ACCOUNT_KEY_PATH: str = "/app/google_creds.json"
    SHEET_ID: str


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    host: str = "localhost"
    port: int = 6379
    db: int = 0

    @property
    def dsn(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


class OpenAISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OPENAI_")

    API_KEY: str
    API_BASE: str | None = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    BOT_TOKEN: str
    ADMIN_TELEGRAM_IDS: List[int] = Field(default_factory=list)
    redis: RedisSettings = RedisSettings()
    google: GoogleSettings = GoogleSettings()
    openai: OpenAISettings = OpenAISettings()

    @field_validator("ADMIN_TELEGRAM_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: str | list) -> list[int]:
        if isinstance(v, str):
            # Handle JSON string "[1, 2]"
            if v.startswith("[") and v.endswith("]"):
                return json.loads(v)
            # Handle comma-separated string "1,2"
            return [int(i.strip()) for i in v.split(",")]
        return v


settings = Settings()
