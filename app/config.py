"""Application configuration and environment loading."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


class AppConfig(BaseModel):
    """Runtime settings sourced from environment variables."""

    openai_api_key: str | None = Field(default=os.getenv("OPENAI_API_KEY"))
    openai_model: str = Field(default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    openai_timeout_seconds: float = Field(default=_env_float("OPENAI_TIMEOUT_SECONDS", 20.0))
    app_host: str = Field(default=os.getenv("APP_HOST", "0.0.0.0"))
    app_port: int = Field(default=_env_int("APP_PORT", 8000))
    route_log_path: str = Field(default=os.getenv("ROUTE_LOG_PATH", "route_log.jsonl"))


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig()
