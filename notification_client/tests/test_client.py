import json
from datetime import UTC, datetime

import httpx
import pytest
from pydantic import SecretStr

from src.client import (
    AuthenticationError,
    consume_notifications,
    obtain_access_token,
    obtain_ws_ticket,
)
from src.core.config import ClientSettings
from src.schemas import RecentNotificationIds


@pytest.fixture
def settings() -> ClientSettings:
    return ClientSettings(
        notification_ws_url="ws://localhost:8001/ws/notifications",
        api_base_url="http://localhost:8000",
        notification_email="organizer@example.com",
        notification_password=SecretStr("password"),
        notification_token=None,
    )


@pytest.mark.asyncio
async def test_obtain_token_posts_real_login_payload(settings):
    received = []

    def handle(request: httpx.Request) -> httpx.Response:
        received.append(request)
        return httpx.Response(200, json={"access_token": "sample.jwt", "token_type": "bearer"})

    # Inject an HTTP client with an in-memory transport. No monkeypatch required.
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        assert await obtain_access_token(settings, client) == "sample.jwt"

    assert len(received) == 1
    assert received[0].url.path == "/api/v1/auth/login"
    assert json.loads(received[0].content) == {
        "email": "organizer@example.com",
        "password": "password",
    }


@pytest.mark.asyncio
async def test_invalid_credentials_fail_fast(settings):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(401))
    ) as client:
        with pytest.raises(AuthenticationError, match="credentials"):
            await obtain_access_token(settings, client)


@pytest.mark.asyncio
async def test_static_token_fallback():
    settings = ClientSettings(
        notification_token=SecretStr("test-token"),
        notification_email=None,
        notification_password=None,
    )
    async with httpx.AsyncClient() as client:
        assert await obtain_access_token(settings, client) == "test-token"


@pytest.mark.asyncio
async def test_obtain_ticket_exchanges_access_token(settings):
    received = []

    def handle(request: httpx.Request) -> httpx.Response:
        received.append(request)
        return httpx.Response(201, json={"ticket": "one-time-ticket", "expires_in": 60})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        assert await obtain_ws_ticket(settings, client, "sample.jwt") == "one-time-ticket"

    assert len(received) == 1
    assert received[0].method == "POST"
    assert str(received[0].url) == settings.notification_ticket_url
    assert received[0].headers["Authorization"] == "Bearer sample.jwt"


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403])
async def test_rejected_access_token_gets_no_ticket(settings, status_code):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(status_code))
    ) as client:
        with pytest.raises(AuthenticationError, match="rejected the access token"):
            await obtain_ws_ticket(settings, client, "expired.jwt")


@pytest.mark.asyncio
async def test_missing_ticket_endpoint_fails_fast(settings):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(404))
    ) as client:
        with pytest.raises(RuntimeError, match="NOTIFICATION_TICKET_URL"):
            await obtain_ws_ticket(settings, client, "sample.jwt")


def payload(notification_id: int) -> str:
    return json.dumps(
        {
            "type": "notification",
            "id": notification_id,
            "event_type": "registration.created",
            "title": "Новая регистрация",
            "text": "Участник записался",
            "data": {"event_id": 7},
            "created_at": datetime(2026, 11, 24, 12, 0, tzinfo=UTC).isoformat(),
        },
        ensure_ascii=False,
    )


@pytest.mark.asyncio
async def test_consume_validates_prints_and_ignores_duplicates():
    async def messages():
        yield payload(1)
        yield payload(1)  # duplicate within same connection
        yield b"invalid-json"
        yield payload(2).encode()

    displayed = []
    await consume_notifications(messages(), RecentNotificationIds(), display=displayed.append)
    assert len(displayed) == 2
    assert "Новая регистрация" in displayed[0]
    assert "Участник записался" in displayed[1]


def test_recent_ids_are_bounded():
    seen = RecentNotificationIds(capacity=2)
    assert seen.is_new(10)
    assert not seen.is_new(10)
    assert seen.is_new(11)
    assert seen.is_new(12)
    assert seen.is_new(10)  # oldest ID was evicted


@pytest.mark.asyncio
async def test_connect_sends_ticket_header_and_receives_message():
    """Real WebSocket handshake over localhost; no RabbitMQ or Docker required."""
    import asyncio
    from contextlib import suppress

    from websockets.asyncio.server import serve

    from src.client import run_client

    received = asyncio.Event()
    displayed = []
    auth_headers = []

    async def handler(websocket):
        auth_headers.append(websocket.request.headers.get("Authorization"))
        await websocket.send(payload(42))
        await websocket.wait_closed()

    def capture_output(text: str) -> None:
        displayed.append(text)
        received.set()

    ticket_requests = []

    def issue_ticket(request: httpx.Request) -> httpx.Response:
        ticket_requests.append(request.headers["Authorization"])
        return httpx.Response(201, json={"ticket": "one-time-ticket", "expires_in": 60})

    async with serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        settings = ClientSettings(
            notification_ws_url=f"ws://127.0.0.1:{port}/ws/notifications",
            notification_token=SecretStr("my-access-jwt"),
            notification_email=None,
            notification_password=None,
        )
        task = asyncio.create_task(
            run_client(
                settings,
                display=capture_output,
                http_transport=httpx.MockTransport(issue_ticket),
            )
        )
        try:
            await asyncio.wait_for(received.wait(), timeout=3)
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    # The access token goes only to the ticket endpoint; the WebSocket gets the ticket
    assert ticket_requests == ["Bearer my-access-jwt"]
    assert auth_headers == ["Bearer one-time-ticket"]
    assert len(displayed) == 1
    assert "Уведомление #42" in displayed[0]
    assert "Новая регистрация" in displayed[0]
