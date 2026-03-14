"""FastAPI entrypoint for AI Prompt Router Service."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.classifier import classify_intent
from app.config import get_config
from app.logger import append_route_log, get_app_logger
from app.router import EMPTY_MESSAGE_RESPONSE, route_and_respond

app = FastAPI(
    title="AI Prompt Router Service",
    description="Routes user messages to specialized AI personas via intent classification.",
    version="1.0.0",
)
logger = get_app_logger("ai_prompt_router.api")


class RouteRequest(BaseModel):
    message: str = Field(..., description="User message to classify and route")


class RouteResponse(BaseModel):
    intent: str
    confidence: float
    final_response: str


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "AI Prompt Router Service", "status": "running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/route", response_model=RouteResponse)
def route_message(payload: RouteRequest) -> RouteResponse:
    """Classify intent, route the request, and persist a JSONL route log."""

    message = payload.message.strip() if payload.message else ""

    if not message:
        fallback = {"intent": "unclear", "confidence": 0.0}
        final_response = EMPTY_MESSAGE_RESPONSE
        append_route_log(
            {
                "intent": fallback["intent"],
                "confidence": fallback["confidence"],
                "user_message": payload.message,
                "final_response": final_response,
            }
        )
        return RouteResponse(
            intent=fallback["intent"],
            confidence=fallback["confidence"],
            final_response=final_response,
        )

    try:
        intent_result = classify_intent(message)
        final_response = route_and_respond(message, intent_result)

        append_route_log(
            {
                "intent": intent_result.get("intent", "unclear"),
                "confidence": float(intent_result.get("confidence", 0.0)),
                "user_message": message,
                "final_response": final_response,
            }
        )

        return RouteResponse(
            intent=str(intent_result.get("intent", "unclear")),
            confidence=float(intent_result.get("confidence", 0.0)),
            final_response=final_response,
        )
    except Exception as exc:  # pragma: no cover - hard safety boundary
        logger.error("Routing pipeline failed unexpectedly: %s", exc)
        fallback_response = "The service encountered an internal error. Please try again shortly."

        append_route_log(
            {
                "intent": "unclear",
                "confidence": 0.0,
                "user_message": message,
                "final_response": fallback_response,
            }
        )

        return RouteResponse(intent="unclear", confidence=0.0, final_response=fallback_response)


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run("app.main:app", host=config.app_host, port=config.app_port, reload=False)
