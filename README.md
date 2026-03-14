# Build an LLM-Powered Prompt Router for Intent Classification

A production-oriented FastAPI backend that routes user messages to specialized AI personas through a two-step workflow:

1. Intent classification
2. Persona-based response generation

The service is designed for reliability. It handles malformed model outputs, empty input, missing environment variables, and external API failures without crashing.

## Project Overview

The system accepts a message, classifies it into one of five intents, and then routes it to a domain persona:

- `code`
- `data`
- `writing`
- `career`
- `unclear`

If intent is `unclear`, the service does not guess. It asks a clarification question.

## Architecture

### Two-Step AI Workflow

1. **Intent Classification** (`app/classifier.py`)
   - Calls the LLM with a compact classification prompt.
   - Expects JSON with:
     - `intent`
     - `confidence`
   - Parses direct JSON and embedded JSON defensively.
   - Falls back to:
     ```json
     { "intent": "unclear", "confidence": 0.0 }
     ```
     when parsing fails.

2. **Routing + Response** (`app/router.py`)
   - Maps intent to a persona prompt from `app/prompts.py`.
   - Calls LLM again with selected persona system prompt.
   - Returns clarification text for `unclear` intent.

### Modules

- `app/main.py`: FastAPI endpoints and orchestration.
- `app/classifier.py`: Intent classification and robust JSON parsing.
- `app/router.py`: Persona routing and final response generation.
- `app/prompts.py`: Centralized system prompts.
- `app/llm_client.py`: OpenAI wrapper with failure handling.
- `app/logger.py`: App logger and JSONL route logging.
- `app/config.py`: Environment config loading.

## Project Structure

```text
Build an LLM-Powered Prompt Router for Intent Classification/
|-- app/
|   |-- __init__.py
|   |-- main.py
|   |-- router.py
|   |-- classifier.py
|   |-- prompts.py
|   |-- llm_client.py
|   |-- logger.py
|   |-- config.py
|-- tests/
|   |-- test_router.py
|-- route_log.jsonl
|-- requirements.txt
|-- Dockerfile
|-- docker-compose.yml
|-- README.md
|-- .env.example
```

## Environment Variables

Copy `.env.example` to `.env` and provide values:

- `OPENAI_API_KEY`: OpenAI API key.
- `OPENAI_MODEL`: Model name (default: `gpt-4o-mini`).
- `OPENAI_TIMEOUT_SECONDS`: Request timeout in seconds.
- `APP_HOST`: Host for Uvicorn.
- `APP_PORT`: Port for Uvicorn.
- `ROUTE_LOG_PATH`: JSONL log file location.

## Local Setup

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

### 2) Configure environment

```bash
cp .env.example .env
```

Then edit `.env` and set `OPENAI_API_KEY`.

### 3) Run service

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Service endpoints:

- `GET /health`
- `POST /route`

## Docker Setup

Run with:

```bash
docker compose up --build
```

The API is exposed on port `8000`.

## API Usage

### Request

```bash
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I optimize this SQL query?"}'
```

### Example Response

```json
{
  "intent": "code",
  "confidence": 0.92,
  "final_response": "You can start by adding an index on ..."
}
```

### Unclear Request Example

```json
{
  "intent": "unclear",
  "confidence": 0.0,
  "final_response": "Could you clarify your request? Are you asking for help with coding, data analysis, writing, or career advice?"
}
```

## Logging

Each request appends one JSON line into `route_log.jsonl`:

```json
{"intent":"data","confidence":0.88,"user_message":"Analyze churn trends","final_response":"..."}
{"intent":"unclear","confidence":0.0,"user_message":"Help me","final_response":"Could you clarify your request?..."}
```

This format is easy to ingest in ELK, Datadog, BigQuery, or custom analytics pipelines.

## Testing

Run tests:

```bash
pytest -q
```

Test coverage includes:

- malformed JSON classification fallback
- empty message handling
- unclear-intent clarification behavior
- LLM unavailability fallback
- API behavior over 15+ sample user prompts:
  - coding
  - data analysis
  - writing feedback
  - career guidance
  - ambiguous prompts

## Design Decisions

- **Prompt separation**: All system prompts live in `prompts.py` for maintainability.
- **Failure-safe defaults**: Invalid model output does not propagate runtime errors.
- **Resilient LLM boundary**: API and OpenAI failures return user-safe fallback responses.
- **Append-only logs**: JSONL log strategy supports stream processing and observability.
- **Minimal coupling**: Classification, routing, model access, and transport are isolated modules.
