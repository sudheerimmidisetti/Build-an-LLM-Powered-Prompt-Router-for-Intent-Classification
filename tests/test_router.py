from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.classifier as classifier_module
import app.main as main_module
import app.router as router_module
from app.classifier import classify_intent
from app.config import AppConfig
from app.llm_client import LLMClient
from app.prompts import UNCLEAR_RESPONSE
from app.router import route_and_respond

client = TestClient(main_module.app)

TEST_MESSAGES: list[tuple[str, str]] = [
    ("How do I implement JWT authentication in FastAPI?", "code"),
    ("Write a Python function to merge two sorted arrays.", "code"),
    ("Find the bug in this SQL query and optimize it.", "code"),
    ("Can you analyze this monthly sales data trend?", "data"),
    ("What chart should I use to compare conversion rates by channel?", "data"),
    ("Is there a correlation between ad spend and signups?", "data"),
    ("Give feedback on the tone of my cover letter.", "writing"),
    ("How can I make this paragraph clearer and more concise?", "writing"),
    ("Please check grammar issues in this email draft.", "writing"),
    ("I want to transition from QA to backend development.", "career"),
    ("What should I focus on to get a data engineer role?", "career"),
    ("How do I prepare for system design interviews?", "career"),
    ("Can you help me with this?", "unclear"),
    ("I am stuck, not sure where to start.", "unclear"),
    ("Need guidance.", "unclear"),
]


def test_sample_message_count() -> None:
    assert len(TEST_MESSAGES) >= 15


def test_classify_intent_defaults_for_empty_message() -> None:
    result = classify_intent("   ")
    assert result == {"intent": "unclear", "confidence": 0.0}


def test_classify_intent_defaults_for_malformed_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        classifier_module.llm_client,
        "complete",
        lambda *args, **kwargs: "intent=code confidence=0.9",
    )

    result = classify_intent("Build a REST API in Flask")
    assert result == {"intent": "unclear", "confidence": 0.0}


def test_classify_intent_parses_embedded_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        classifier_module.llm_client,
        "complete",
        lambda *args, **kwargs: "Result: {\"intent\": \"data\", \"confidence\": 0.84}",
    )

    result = classify_intent("Analyze this cohort retention table")
    assert result == {"intent": "data", "confidence": 0.84}


def test_route_unclear_returns_clarification() -> None:
    response = route_and_respond("Can you help me?", {"intent": "unclear", "confidence": 0.2})
    assert response == UNCLEAR_RESPONSE


def test_route_returns_service_fallback_on_llm_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(router_module.llm_client, "complete", lambda *args, **kwargs: None)
    response = route_and_respond("How to write a unit test in pytest?", {"intent": "code", "confidence": 0.9})
    assert "could not generate" in response.lower()


def test_route_empty_message_guard() -> None:
    response = route_and_respond("   ", {"intent": "code", "confidence": 1.0})
    assert "non-empty" in response.lower()


def test_llm_client_gracefully_disables_without_key() -> None:
    config = AppConfig(openai_api_key=None)
    local_client = LLMClient(config=config)
    assert local_client.complete("sys", "hello") is None


@pytest.mark.parametrize("message, expected_intent", TEST_MESSAGES)
def test_route_endpoint_with_varied_messages(
    monkeypatch: pytest.MonkeyPatch,
    message: str,
    expected_intent: str,
) -> None:
    monkeypatch.setattr(
        main_module,
        "classify_intent",
        lambda user_message: {"intent": expected_intent, "confidence": 0.91},
    )
    monkeypatch.setattr(
        main_module,
        "route_and_respond",
        lambda user_message, intent_result: f"handled:{intent_result['intent']}",
    )

    response = client.post("/route", json={"message": message})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == expected_intent
    assert body["confidence"] == pytest.approx(0.91)
    assert body["final_response"] == f"handled:{expected_intent}"


def test_route_endpoint_handles_empty_message() -> None:
    response = client.post("/route", json={"message": "   "})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "unclear"
    assert body["confidence"] == 0.0
    assert "non-empty" in body["final_response"].lower()
