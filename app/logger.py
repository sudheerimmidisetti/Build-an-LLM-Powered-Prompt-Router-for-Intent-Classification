"""Structured logging helpers for request routing."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import Lock
from typing import Any

from app.config import get_config

_log_write_lock = Lock()


def get_app_logger(name: str = "ai_prompt_router") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def append_route_log(entry: dict[str, Any]) -> None:
    """Append one JSON object per line to the route log file."""

    config = get_config()
    log_path = Path(config.route_log_path)

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        # If parent directory creation fails, continue without crashing.
        return

    try:
        with _log_write_lock:
            with log_path.open("a", encoding="utf-8") as file_obj:
                file_obj.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        # Logging failures should never break API requests.
        return
