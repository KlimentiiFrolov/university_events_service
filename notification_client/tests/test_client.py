import json
from datetime import UTC, datetime

import httpx
import pytest
from pydantic import SecretStr

from src.client import AuthenticationError, consume_notifications, obtain_access_token
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
async def test_obtain_token_posts_real_login_payload(monkeypatch, settings):
    received = []

    def handle(request: httpx.Request) -> httpx.Response:
        received.append(request)
        return httpx.Response(200, json={"access_token": "sample.jwt", "token_type": "bearer"})

    # Use an in-memory transport to validate our outgoing HTTP request.
    class FakeClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            super().__init__(transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr("src.client.httpx.AsyncClient", FakeClient)
    assert await obtain_access_token(settings) == "sample.jwt"
    assert len(received) == 1
    assert received[0].url.path == "/api/v1/auth/login"
    assert json.loads(received[0].content) == {
        "email": "organizer@example.com",
        "password": "password",
    }


@pytest.mark.asyncio
async def test_invalid_credentials_fail_fast(monkeypatch, settings):
    class FakeClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            super().__init__(transport=httpx.MockTransport(lambda _: httpx.Response(401)), **kwargs)

    monkeypatch.setattr("src.client.httpx.AsyncClient", FakeClient)
    with pytest.raises(AuthenticationError, match="credentials"):
        await obtain_access_token(settings)


@pytest.mark.asyncio
async def test_static_token_fallback():
    settings = ClientSettings(
        notification_token=SecretStr("test-token"),
        notification_email=None,
        notification_password=None,
    )
    assert await obtain_access_token(settings) == "test-token"


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
async def test_connect_sends_bearer_header_and_receives_message(monkeypatch):
    """Real WebSocket handshake over localhost; no RabbitMQ or Docker required."""
    import asyncio
    from contextlib import suppress

    from websockets.asyncio.server import serve
    from src.client import run_client

    received = asyncio.Event()
    sent = []
    auth_headers = []

    async def handler(websocket):
        auth_headers.append(websocket.request.headers.get("Authorization"))
        await websocket.send(payload(42))
        await websocket.wait_closed()

    async def capture(messages, seen):
        async for raw in messages:
            sent.append(raw)
            received.set()
            return

    monkeypatch.setattr("src.client.consume_notifications", capture)

    async with serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        settings = ClientSettings(
            notification_ws_url=f"ws://127.0.0.1:{port}/ws/notifications",
            notification_token=SecretStr("my-access-jwt"),
            notification_email=None,
            notification_password=None,
        )
        task = asyncio.create_task(run_client(settings))
        try:
            await asyncio.wait_for(received.wait(), timeout=3)
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    assert auth_headers == ["Bearer my-access-jwt"]
    assert json.loads(sent[0])["id"] == 42
