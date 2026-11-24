# notification_client

Standalone Python console WebSocket client for lab 4.

It logs in through the existing API Service endpoint (`POST /api/v1/auth/login`) to
obtain a short-lived access token, then opens `/ws/notifications` using the
`Authorization: Bearer <access_token>` header. Incoming messages are validated,
formatted, and printed. The client suppresses recent duplicate IDs in memory and
reconnects after temporary errors.

## Local development (interactive credentials)

From `notification_client/`, install dependencies and launch the client:

```bash
uv sync
uv run python -m src.main
```

If no credentials are configured, an interactive terminal prompts for the email
and password of an **existing user**. The password is entered without echoing
it on screen. You do **not** need to edit `.env` to switch accounts.

When running directly on Windows, create `notification_client/.env` from
`.env.template` and override **only the service URLs**:

```dotenv
API_BASE_URL=http://localhost:8080
NOTIFICATION_WS_URL=ws://localhost:8080/ws/notifications
```

Alternatively, you may configure `NOTIFICATION_EMAIL` and
`NOTIFICATION_PASSWORD` in this `.env` (or as environment variables) to bypass
interactive login, or use `NOTIFICATION_TOKEN` for a pre-issued JWT. A static
token cannot automatically refresh on expiry; credentials allow re-login on each
reconnect. **Never commit `.env`**.

For the `registration.created` demo, use the event organizer's account because
registration notifications are sent to the organizer, not to the participant.

## Docker Compose (non-interactive)

Docker containers have no interactive terminal by default, so configure
`NOTIFICATION_EMAIL` and `NOTIFICATION_PASSWORD` (or `NOTIFICATION_TOKEN`) in
`notification_client/.env` before starting Compose. Use the Docker network URLs
from `.env.template`:

```dotenv
API_BASE_URL=http://api_service:8000
NOTIFICATION_WS_URL=ws://notification_service:8001/ws/notifications
```

Ensure root `.env` and other service `.env` files required by Compose exist.
From the monorepo root:

```bash
docker compose up -d --build
docker compose logs -f notification_client
```

The client automatically logs in again on reconnect when credentials are used.

## Run tests

From `notification_client/`:

```bash
uv run pytest -q
uv run ruff check .
```

The tests use dependency injection with `httpx.MockTransport` and an in-process
WebSocket server. They don't need running API, RabbitMQ, or Docker containers.

## What the client receives

The WebSocket protocol is JSON containing `type: "notification"`, `id`,
`event_type`, `title`, `text`, `data`, and `created_at`. The server decides the
recipient using the authenticated user ID.

Malformed messages are ignored. Repeated notification IDs are suppressed while
running, up to the most recent 1000 IDs. There is no client acknowledgement (ACK)
in the current Notification Service protocol.
