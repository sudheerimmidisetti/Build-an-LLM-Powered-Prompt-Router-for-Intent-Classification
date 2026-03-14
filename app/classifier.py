"""Intent classification logic for user messages."""

from __future__ import annotations

import json
from typing import Any

from app.llm_client import llm_client
from app.logger import get_app_logger
from app.prompts import CLASSIFIER_SYSTEM_PROMPT

logger = get_app_logger("ai_prompt_router.classifier")

ALLOWED_INTENTS = {"code", "data", "writing", "career", "unclear"}
DEFAULT_INTENT = {"intent": "unclear", "confidence": 0.0}


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    """Parse JSON from direct or embedded model output."""

    raw_text = raw_text.strip()
    if not raw_text:
        return None

    try:
        payload = json.loads(raw_text)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    start_index = raw_text.find("{")
    while start_index != -1:
        depth = 0
        for end_index in range(start_index, len(raw_text)):
            char = raw_text[end_index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidate = raw_text[start_index : end_index + 1]
                    try:
                        payload = json.loads(candidate)
                        if isinstance(payload, dict):
                            return payload
                    except json.JSONDecodeError:
                        break
        start_index = raw_text.find("{", start_index + 1)

    return None


def _normalize_intent_payload(payload: dict[str, Any]) -> dict[str, Any]:
    intent = str(payload.get("intent", "unclear")).strip().lower()
    if intent not in ALLOWED_INTENTS:
        intent = "unclear"

    raw_confidence = payload.get("confidence", 0.0)
    try:
        confidence = float(raw_confidence)
    except (TypeError, ValueError):
        confidence = 0.0

    confidence = max(0.0, min(1.0, confidence))
    return {"intent": intent, "confidence": confidence}


def classify_intent(message: str) -> dict[str, Any]:
    """
    Classify the user message into one of the supported intents.

    Returns a safe default when the response cannot be parsed.
    """

    if not message or not message.strip():
        return DEFAULT_INTENT.copy()

    try:
        raw_output = llm_client.complete(
            system_prompt=CLASSIFIER_SYSTEM_PROMPT,
            user_message=message,
            temperature=0.0,
            max_tokens=80,
            response_format={"type": "json_object"},
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.error("Intent classification call failed: %s", exc)
        return DEFAULT_INTENT.copy()

    if not raw_output:
        return DEFAULT_INTENT.copy()

    parsed_payload = _extract_json_object(raw_output)
    if parsed_payload is None:
        logger.warning("Classifier returned malformed JSON; using fallback intent.")
        return DEFAULT_INTENT.copy()

    return _normalize_intent_payload(parsed_payload)
