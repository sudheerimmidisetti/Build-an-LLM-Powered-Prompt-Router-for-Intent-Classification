"""OpenAI client wrapper with resilient failure handling."""

from __future__ import annotations

from typing import Any

from app.config import AppConfig, get_config
from app.logger import get_app_logger

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - guarded for environments without openai
    OpenAI = None  # type: ignore[assignment]


class LLMClient:
    """Small wrapper that isolates external API handling from business logic."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or get_config()
        self.logger = get_app_logger("ai_prompt_router.llm")
        self._client = None

        if not self.config.openai_api_key:
            self.logger.warning("OPENAI_API_KEY is not set; LLM calls are disabled.")
            return

        if OpenAI is None:
            self.logger.error("openai package is unavailable; LLM calls are disabled.")
            return

        try:
            self._client = OpenAI(api_key=self.config.openai_api_key)
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            self.logger.error("Failed to initialize OpenAI client: %s", exc)
            self._client = None

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.2,
        max_tokens: int = 500,
        response_format: dict[str, Any] | None = None,
    ) -> str | None:
        """Execute a chat completion and return text content or None."""

        if self._client is None:
            return None

        if not user_message.strip():
            return None

        try:
            request_payload: dict[str, Any] = {
                "model": self.config.openai_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout": self.config.openai_timeout_seconds,
            }
            if response_format is not None:
                request_payload["response_format"] = response_format

            response = self._client.chat.completions.create(**request_payload)
        except Exception as exc:
            self.logger.error("OpenAI API call failed: %s", exc)
            return None

        try:
            first_choice = response.choices[0]
            content = first_choice.message.content
            if not content or not isinstance(content, str):
                return None
            return content.strip()
        except Exception:
            self.logger.error("Unexpected API response format from OpenAI.")
            return None


llm_client = LLMClient()
