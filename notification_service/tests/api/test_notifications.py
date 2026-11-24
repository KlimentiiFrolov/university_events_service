import asyncio
import time
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from notifications.lifespan import NotificationLifespan
from notifications.models import Notification
from notifications.websocket.manager import ConnectionManager

from ..tokens import USER_ID, bearer, make_token

OTHER_USER_ID = 8
URL = "/ws/notifications"


@pytest.fixture
def manager(notification_lifespan: NotificationLifespan) -> ConnectionManager:
    return notification_lifespan.manager


def issue_ticket(client: TestClient) -> str:
    """Получить тикет так же, как клиент: POST /ws/tickets с access-токеном."""
    response = client.post("/ws/tickets", headers=bearer(make_token()))
    assert response.status_code == 201
    return response.json()["ticket"]


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


def receive_delivered(
    websocket,
    session_maker: async_sessionmaker[AsyncSession],
) -> dict[str, Any]:
    """Получить уведомление и дождаться, пока сервер отметит его доставленным.

    Иначе тест закроет соединение, пока сервер ещё пишет в БД, и TestClient оборвёт
    запрос asyncpg на остановке своего event loop.
    """
    message = websocket.receive_json()
    wait_until(lambda: is_delivered(session_maker, message["id"]))
    return message


# --- авторизация (подробно - в test_dependencies.py) ---


def test_ticket_from_endpoint_opens_connection(client: TestClient, manager: ConnectionManager):
    with client.websocket_connect(URL, headers=bearer(issue_ticket(client))):
        wait_until(lambda: manager.is_connected(USER_ID))


def test_ticket_in_query_opens_connection(client: TestClient, manager: ConnectionManager):
    with client.websocket_connect(f"{URL}?ticket={issue_ticket(client)}"):
        wait_until(lambda: manager.is_connected(USER_ID))


@pytest.mark.parametrize(
    "headers",
    [{}, bearer(make_token())],
    ids=["no ticket", "access token instead of ticket"],
)
def test_connection_without_ticket_is_rejected_with_1008(
    client: TestClient,
    headers: dict[str, str],
):
    with (
        pytest.raises(WebSocketDisconnect) as error,
        client.websocket_connect(URL, headers=headers),
    ):
        pass

    assert error.value.code == 1008


# --- досылка ---


def test_undelivered_notifications_are_sent_on_connect(client: TestClient, app_session_maker):
    first, second, _ = add_notifications(app_session_maker, USER_ID, USER_ID, OTHER_USER_ID)

    with client.websocket_connect(URL, headers=bearer(issue_ticket(client))) as websocket:
        received = [
            receive_delivered(websocket, app_session_maker),
            receive_delivered(websocket, app_session_maker),
        ]

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

    with client.websocket_connect(URL, headers=bearer(issue_ticket(client))) as websocket:
        websocket.receive_json()
        wait_until(lambda: is_delivered(app_session_maker, notification_id))


def test_delivered_notification_is_not_sent_again(client: TestClient, app_session_maker):
    ids = add_notifications(app_session_maker, USER_ID)
    delivered = ids[0]
    with client.websocket_connect(URL, headers=bearer(issue_ticket(client))) as websocket:
        websocket.receive_json()
        wait_until(lambda: is_delivered(app_session_maker, delivered))

    ids = add_notifications(app_session_maker, USER_ID)
    new = ids[0]
    with client.websocket_connect(URL, headers=bearer(issue_ticket(client))) as websocket:
        message = receive_delivered(websocket, app_session_maker)

    assert message["id"] == new


def test_other_users_notifications_stay_undelivered(client: TestClient, app_session_maker):
    own, foreign = add_notifications(app_session_maker, USER_ID, OTHER_USER_ID)

    with client.websocket_connect(URL, headers=bearer(issue_ticket(client))) as websocket:
        websocket.receive_json()
        wait_until(lambda: is_delivered(app_session_maker, own))

    assert is_delivered(app_session_maker, foreign) is False


def test_client_message_does_not_close_connection(
    client: TestClient,
    manager: ConnectionManager,
    app_session_maker,
):
    add_notifications(app_session_maker, USER_ID)

    with client.websocket_connect(URL, headers=bearer(issue_ticket(client))) as websocket:
        receive_delivered(websocket, app_session_maker)
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

    with client.websocket_connect(URL, headers=bearer(issue_ticket(client))) as websocket:
        # Досылка идёт после регистрации: раз сообщение пришло, подключение уже в реестре
        receive_delivered(websocket, app_session_maker)
        assert manager.is_connected(USER_ID) is True

    wait_until(lambda: not manager.is_connected(USER_ID))
