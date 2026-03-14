"""Intent-based routing to domain-specific AI personas."""

from __future__ import annotations

from typing import Any

from app.llm_client import llm_client
from app.prompts import PERSONA_PROMPTS, UNCLEAR_RESPONSE


SERVICE_UNAVAILABLE_RESPONSE = (
    "I could not generate a response right now. Please try again in a moment."
)
EMPTY_MESSAGE_RESPONSE = "Please provide a non-empty message so I can help you."


def route_and_respond(message: str, intent: dict[str, Any]) -> str:
    """
    Route a message to the correct persona and return the final model response.

    If intent is unclear, the function asks for clarification instead of guessing.
    """

    if not message or not message.strip():
        return EMPTY_MESSAGE_RESPONSE

    selected_intent = str(intent.get("intent", "unclear")).strip().lower() if intent else "unclear"

    if selected_intent == "unclear":
        return UNCLEAR_RESPONSE

    system_prompt = PERSONA_PROMPTS.get(selected_intent)
    if not system_prompt:
        return UNCLEAR_RESPONSE

    model_output = llm_client.complete(
        system_prompt=system_prompt,
        user_message=message,
        temperature=0.4,
        max_tokens=700,
    )

    if not model_output:
        return SERVICE_UNAVAILABLE_RESPONSE

    return model_output.strip()
