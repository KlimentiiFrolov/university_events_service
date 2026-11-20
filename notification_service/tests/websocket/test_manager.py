from typing import Any

import pytest

from src.notifications.websocket.manager import ConnectionManager

USER_ID = 7
OTHER_USER_ID = 8
PAYLOAD = {"type": "notification", "id": 1}


class FakeWebSocket:
    """Вместо WebSocket: записывает отправленное, умеет «отвалиться»."""

    def __init__(self, *, broken: bool = False) -> None:
        self.sent: list[dict[str, Any]] = []
        self.broken = broken

    async def send_json(self, data: dict[str, Any]) -> None:
        if self.broken:
            raise RuntimeError("connection closed")
        self.sent.append(data)


@pytest.fixture
def manager() -> ConnectionManager:
    return ConnectionManager()


async def test_message_is_delivered_only_to_its_user(manager: ConnectionManager):
    recipient = FakeWebSocket()
    other = FakeWebSocket()
    manager.connect(USER_ID, recipient)
    manager.connect(OTHER_USER_ID, other)

    delivered = await manager.send_to_user(USER_ID, PAYLOAD)

    assert delivered == 1
    assert recipient.sent == [PAYLOAD]
    assert other.sent == []


async def test_all_connections_of_user_receive_message(manager: ConnectionManager):
    first_tab = FakeWebSocket()
    second_tab = FakeWebSocket()
    manager.connect(USER_ID, first_tab)
    manager.connect(USER_ID, second_tab)

    delivered = await manager.send_to_user(USER_ID, PAYLOAD)

    assert delivered == 2
    assert first_tab.sent == [PAYLOAD]
    assert second_tab.sent == [PAYLOAD]


async def test_sending_to_offline_user_delivers_nothing(manager: ConnectionManager):
    assert await manager.send_to_user(USER_ID, PAYLOAD) == 0


async def test_broken_connection_is_dropped(manager: ConnectionManager):
    alive = FakeWebSocket()
    broken = FakeWebSocket(broken=True)
    manager.connect(USER_ID, alive)
    manager.connect(USER_ID, broken)

    delivered = await manager.send_to_user(USER_ID, PAYLOAD)
    second_round = await manager.send_to_user(USER_ID, PAYLOAD)

    assert delivered == 1
    assert second_round == 1
    assert alive.sent == [PAYLOAD, PAYLOAD]


def test_disconnect_last_connection_marks_user_offline(manager: ConnectionManager):
    websocket = FakeWebSocket()
    manager.connect(USER_ID, websocket)

    manager.disconnect(USER_ID, websocket)

    assert manager.is_connected(USER_ID) is False


def test_disconnect_one_of_connections_keeps_user_online(manager: ConnectionManager):
    first_tab = FakeWebSocket()
    manager.connect(USER_ID, first_tab)
    manager.connect(USER_ID, FakeWebSocket())

    manager.disconnect(USER_ID, first_tab)

    assert manager.is_connected(USER_ID) is True


def test_disconnect_unknown_connection_does_nothing(manager: ConnectionManager):
    manager.disconnect(USER_ID, FakeWebSocket())

    assert manager.is_connected(USER_ID) is False
