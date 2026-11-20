import asyncio
import time
from collections.abc import Callable, Generator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient
from sqlalchemy import NullPool, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.notifications.core.config import AuthSettings
from src.notifications.models import Notification
from src.notifications.websocket.endpoint import build_router
from src.notifications.websocket.manager import ConnectionManager

AUTH = AuthSettings.model_construct(secret_key="test-secret", algorithm="HS256")
USER_ID = 7
OTHER_USER_ID = 8
URL = "/ws/notifications"


def make_token(
    user_id: int = USER_ID,
    *,
    token_type: str = "access",
    expires_in: timedelta = timedelta(minutes=5),
    secret: str = AUTH.secret_key,
) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "type": token_type, "iat": now, "exp": now + expires_in}
    return jwt.encode(payload, secret, algorithm=AUTH.algorithm)


@pytest.fixture
def app_session_maker(db_url: str, clean_db: None) -> async_sessionmaker[AsyncSession]:
    # NullPool: приложение работает в потоке TestClient со своим event loop,
    # соединения из пула другого loop asyncpg не примет
    engine = create_async_engine(db_url, poolclass=NullPool)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def manager() -> ConnectionManager:
    return ConnectionManager()


@pytest.fixture
def client(
    manager: ConnectionManager,
    app_session_maker: async_sessionmaker[AsyncSession],
) -> Generator[TestClient, None, None]:
    app = FastAPI()
    app.include_router(build_router(manager, AUTH, session_factory=app_session_maker))
    with TestClient(app) as test_client:
        yield test_client


def add_notifications(
    session_maker: async_sessionmaker[AsyncSession],
    *user_ids: int,
) -> list[int]:
    async def _add() -> list[int]:
        async with session_maker() as session, session.begin():
            notifications = [
                Notification(
                    message_id=uuid4(),
                    user_id=user_id,
                    type="registration.created",
                    title=f"title {index}",
                    text="text",
                    data={"event_id": 1},
                )
                for index, user_id in enumerate(user_ids)
            ]
            session.add_all(notifications)
            await session.flush()
            return [notification.id for notification in notifications]

    return asyncio.run(_add())


def is_delivered(session_maker: async_sessionmaker[AsyncSession], notification_id: int) -> bool:
    async def _check() -> bool:
        async with session_maker() as session:
            delivered_at = await session.scalar(
                select(Notification.delivered_at).where(Notification.id == notification_id)
            )
            return delivered_at is not None

    return asyncio.run(_check())


def wait_until(condition: Callable[[], bool], timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError("Condition not met in time")
        time.sleep(0.05)


# --- авторизация ---


@pytest.mark.parametrize(
    "token",
    [
        "",
        "not-a-jwt",
        make_token(secret="other-secret"),
        make_token(expires_in=timedelta(minutes=-1)),
        make_token(token_type="refresh"),
        make_token(user_id=0),
    ],
    ids=["missing", "garbage", "wrong secret", "expired", "refresh type", "bad subject"],
)
def test_invalid_token_is_rejected_with_1008(client: TestClient, token: str):
    with (
        pytest.raises(WebSocketDisconnect) as error,
        client.websocket_connect(f"{URL}?token={token}"),
    ):
        pass

    assert error.value.code == 1008


# --- досылка ---


def test_undelivered_notifications_are_sent_on_connect(client: TestClient, app_session_maker):
    first, second, _ = add_notifications(app_session_maker, USER_ID, USER_ID, OTHER_USER_ID)

    with client.websocket_connect(f"{URL}?token={make_token()}") as websocket:
        received = [websocket.receive_json(), websocket.receive_json()]

    assert [message["id"] for message in received] == [first, second]
    message = received[0]
    assert message["type"] == "notification"
    assert message["event_type"] == "registration.created"
    assert message["title"] == "title 0"
    assert message["data"] == {"event_id": 1}
    assert message["created_at"]


# --- отметка доставки ---


def test_sent_notifications_are_marked_delivered(client: TestClient, app_session_maker):
    ids = add_notifications(app_session_maker, USER_ID)
    notification_id = ids[0]

    with client.websocket_connect(f"{URL}?token={make_token()}") as websocket:
        websocket.receive_json()
        wait_until(lambda: is_delivered(app_session_maker, notification_id))


def test_delivered_notification_is_not_sent_again(client: TestClient, app_session_maker):
    ids = add_notifications(app_session_maker, USER_ID)
    delivered = ids[0]
    with client.websocket_connect(f"{URL}?token={make_token()}") as websocket:
        websocket.receive_json()
        wait_until(lambda: is_delivered(app_session_maker, delivered))

    ids = add_notifications(app_session_maker, USER_ID)
    new = ids[0]
    with client.websocket_connect(f"{URL}?token={make_token()}") as websocket:
        message = websocket.receive_json()

    assert message["id"] == new


def test_other_users_notifications_stay_undelivered(client: TestClient, app_session_maker):
    own, foreign = add_notifications(app_session_maker, USER_ID, OTHER_USER_ID)

    with client.websocket_connect(f"{URL}?token={make_token()}") as websocket:
        websocket.receive_json()
        wait_until(lambda: is_delivered(app_session_maker, own))

    assert is_delivered(app_session_maker, foreign) is False


def test_client_message_does_not_close_connection(
    client: TestClient,
    manager: ConnectionManager,
    app_session_maker,
):
    add_notifications(app_session_maker, USER_ID)

    with client.websocket_connect(f"{URL}?token={make_token()}") as websocket:
        websocket.receive_json()
        websocket.send_text("hello")
        time.sleep(0.2)
        assert manager.is_connected(USER_ID) is True


# --- реестр подключений ---


def test_connection_is_registered_while_open(
    client: TestClient,
    manager: ConnectionManager,
    app_session_maker,
):
    add_notifications(app_session_maker, USER_ID)

    with client.websocket_connect(f"{URL}?token={make_token()}") as websocket:
        # Досылка идёт после регистрации: раз сообщение пришло, подключение уже в реестре
        websocket.receive_json()
        assert manager.is_connected(USER_ID) is True

    wait_until(lambda: not manager.is_connected(USER_ID))
