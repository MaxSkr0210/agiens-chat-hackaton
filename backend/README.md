# Agiens Backend

FastAPI backend for the universal chat. Uses a **pluggable LLM registry**: add any provider by implementing `LLMProvider` and registering it in `app/main.py`.

## Run locally

PostgreSQL and Redis (optional) must be running. With Docker: `docker compose up postgres redis -d`, then:

```bash
cd backend
pip install -r requirements.txt
export OPENROUTER_API_KEY=sk-or-v1-...
export DATABASE_URL=postgresql+asyncpg://agiens:agiens@localhost:5432/agiens
export REDIS_URL=redis://localhost:6379/0  # optional
uvicorn app.main:app --reload --port 3001
```

## Add a new LLM provider

1. Create `app/llm/<provider>.py` with a class that implements `LLMProvider` (see `app/llm/base.py`).
2. Implement `chat()` (and optionally `stream()`). Use `provider_id` like `"openai"` or `"anthropic"`.
3. In `app/main.py` lifespan, register it: `llm_registry.register(YourProvider(api_key=settings.your_api_key))`.
4. Optionally add config in `app/config.py` (e.g. `openai_api_key`) and pass to the provider.

Model IDs from the frontend can use the form `provider_id/model_name`; the registry routes by prefix. Unrecognized prefixes fall back to OpenRouter when available.

## Docker

Built and run via root `docker-compose.yml` together with the frontend.
