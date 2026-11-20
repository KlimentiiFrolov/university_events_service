FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_NO_DEV=1 \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock* README.md ./
RUN uv sync --no-install-project

COPY . /app
RUN uv sync

EXPOSE 8001

# Миграции БД уведомлений, затем сервис (consumer + WebSocket)
CMD ["sh", "-c", "uv run alembic upgrade head && uv run python -m notifications.main"]
