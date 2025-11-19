from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_PROXY_URL: Optional[str] = None

    # Access control
    ADMIN_IDS: List[int] = []

    # Backend
    # Deprecated in local mode
    BACKEND_BASE_URL: str = "https://parskad.ru"
    REQUEST_TIMEOUT_SECONDS: float = 10.0
    POLL_INTERVAL_SECONDS: float = 1.0

    # Modes: links or download (download acts same as links for now)
    DEFAULT_MODE: str = "links"

    # Limits
    GLOBAL_DAILY_LIMIT: int = 10000
    PER_USER_DAILY_LIMIT: int = 500

    # Logging
    LOG_LEVEL: str = "INFO"

    # Files
    FILES_DIR: str = "files"

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return [int(x) for x in v]
        parts = [p.strip() for p in str(v).split(",") if p.strip()]
        return [int(p) for p in parts]


class RuntimeState(BaseModel):
    backend_base_url: str
    default_mode: str


settings = Settings()
state = RuntimeState(
    backend_base_url=settings.BACKEND_BASE_URL.rstrip("/"),
    default_mode=settings.DEFAULT_MODE,
)


