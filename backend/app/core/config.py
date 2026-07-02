from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PAPER_READER_", env_file=".env")

    data_dir: Path = Field(default=Path("./data"))
    api_base_url: str = Field(default="https://api.openai.com/v1")
    api_key: str = Field(default="")
    chat_model: str = Field(default="gpt-4.1-mini")
    request_timeout_seconds: int = Field(default=120)
    temperature: float = Field(default=0.2)


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
