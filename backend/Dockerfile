# Backend: FastAPI + OpenRouter-ready, extensible LLM API
FROM python:3.12-slim

WORKDIR /app

# System deps (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps (upgrade pip first; retries help with flaky network/PyPI)
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --retries 5 --timeout 60 -r requirements.txt

# App
COPY app/ ./app/
COPY pyproject.toml* ./

ENV PYTHONPATH=/app
EXPOSE 3001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001"]
