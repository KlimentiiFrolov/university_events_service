from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.notifications.models import Notification
from src.notifications.websocket.delivery import push_notifications, push_undelivered
from src.notifications.websocket.manager import ConnectionManager

from .test_manager import FakeWebSocket

ONLINE_USER_ID = 7
OFFLINE_USER_ID = 8


async def add_notifications(
    session_maker: async_sessionmaker[AsyncSession],
    *user_ids: int,
) -> list[Notification]:
    async with session_maker() as session, session.begin():
        notifications = [
            Notification(
                message_id=uuid4(),
                user_id=user_id,
                type="registration.created",
                title="title",
                text="text",
                data={"event_id": 1},
            )
            for user_id in user_ids
        ]
        session.add_all(notifications)
    return notifications


async def is_delivered(session_maker: async_sessionmaker[AsyncSession], notification_id: int) -> bool:
    async with session_maker() as session:
        delivered_at = await session.scalar(
            select(Notification.delivered_at).where(Notification.id == notification_id)
        )
        return delivered_at is not None


async def test_online_user_receives_notification_and_it_is_marked_delivered(session_maker):
    manager = ConnectionManager()
    websocket = FakeWebSocket()
    manager.connect(ONLINE_USER_ID, websocket)
    notifications = await add_notifications(session_maker, ONLINE_USER_ID)
    notification = notifications[0]

    await push_notifications(manager, notifications, session_maker)

    assert len(websocket.sent) == 1
    payload = websocket.sent[0]
    assert payload["type"] == "notification"
    assert payload["id"] == notification.id
    assert await is_delivered(session_maker, notification.id) is True


async def test_offline_user_notification_stays_undelivered(session_maker):
    manager = ConnectionManager()
    online = FakeWebSocket()
    manager.connect(ONLINE_USER_ID, online)
    for_online, for_offline = await add_notifications(session_maker, ONLINE_USER_ID, OFFLINE_USER_ID)

    await push_notifications(manager, [for_online, for_offline], session_maker)

    assert [payload["id"] for payload in online.sent] == [for_online.id]
    assert await is_delivered(session_maker, for_online.id) is True
    assert await is_delivered(session_maker, for_offline.id) is False


async def test_notification_sent_to_broken_connection_stays_undelivered(session_maker):
    manager = ConnectionManager()
    manager.connect(ONLINE_USER_ID, FakeWebSocket(broken=True))
    notifications = await add_notifications(session_maker, ONLINE_USER_ID)

    await push_notifications(manager, notifications, session_maker)

    assert await is_delivered(session_maker, notifications[0].id) is False


async def test_push_undelivered_sends_only_users_undelivered(session_maker):
    manager = ConnectionManager()
    websocket = FakeWebSocket()
    manager.connect(ONLINE_USER_ID, websocket)
    own, already_delivered, _ = await add_notifications(
        session_maker, ONLINE_USER_ID, ONLINE_USER_ID, OFFLINE_USER_ID
    )
    await push_notifications(manager, [already_delivered], session_maker)
    websocket.sent.clear()

    await push_undelivered(manager, ONLINE_USER_ID, session_maker)

    assert [payload["id"] for payload in websocket.sent] == [own.id]
    assert await is_delivered(session_maker, own.id) is True
