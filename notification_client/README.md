# notification_client

Standalone Python console WebSocket client for lab 4.

It uses the existing API Service login endpoint (`POST /api/v1/auth/login`) to obtain an
access token, then connects to Notification Service at `/ws/notifications` with an
`Authorization: Bearer <access_token>` header. It validates messages, prints incoming
notifications, suppresses duplicate IDs in memory, and reconnects after temporary errors.

## Docker Compose

1. From the monorepo root, copy `notification_client/.env.template` to
   `notification_client/.env`.
2. Set `NOTIFICATION_EMAIL` and `NOTIFICATION_PASSWORD` in that `.env` to an *existing*
   user's login credentials. Do not commit this file. For the `registration.created`
   demo, the login user should be the event's organizer.
3. Ensure root `.env` and other service `.env` files required by Compose are present.
4. From the monorepo root:

   ```bash
   docker compose up --build
   docker compose logs -f notification_client
   ```

The client automatically logs in again on reconnect, so an expired JWT isn't reused.
The `notification_client` service defined in the existing `docker-compose.yml` is used
without modification.

## Local development

In `notification_client/.env`, override the URLs for a client running on the host:

```dotenv
API_BASE_URL=http://localhost:8080
NOTIFICATION_WS_URL=ws://localhost:8080/ws/notifications
NOTIFICATION_EMAIL=organizer@example.com
NOTIFICATION_PASSWORD=your-password
```

Then run from `notification_client/`:

```bash
uv sync
uv run python -m src.main
uv run pytest -q
```

If you already have an access JWT, leave email/password empty and set
`NOTIFICATION_TOKEN` instead; note that a static token cannot renew itself.

## What the client receives

The WebSocket protocol is JSON with `type: "notification"`, `id`, `event_type`,
`title`, `text`, `data`, and `created_at`. The server decides who receives each
notification based on the authenticated user ID.

The client ignores malformed messages and suppresses repeated notification IDs
while running. It doesn't acknowledge delivery to the server because the current
Notification Service protocol doesn't support client acknowledgements.
