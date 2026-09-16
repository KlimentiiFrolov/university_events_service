FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_NO_DEV=1 \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-install-project

COPY . /app
RUN uv sync

EXPOSE 8000
CMD ["uv", "run", "python", "-m", "src.main"]
