FROM python:3.11-slim

WORKDIR /app

COPY backend/pyproject.toml ./
RUN pip install --break-system-packages --no-cache-dir ".[dev]"

COPY backend/app ./app
COPY worker/app ./worker_app

CMD ["celery", "-A", "worker_app.celery_app", "worker", "--loglevel=info"]
