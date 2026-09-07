FROM python:3.12-slim

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

CMD ["uv", "run", "python", "-m", "src.main"]
