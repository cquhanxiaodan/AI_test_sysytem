FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --break-system-packages --no-cache-dir ".[dev]"

COPY app ./app
COPY tests ./tests

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
