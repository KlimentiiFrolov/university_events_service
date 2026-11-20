import asyncio
import json
from typing import Any
from uuid import UUID, uuid4

import pytest
from aio_pika.abc import AbstractChannel, AbstractConnection
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from notifications.consumers.notifications import start_consumer
from notifications.core.config import RabbitMQSettings
from notifications.models import Notification
from notifications.websocket.manager import ConnectionManager

from ..websocket.test_manager import FakeWebSocket
from .conftest import Publish, wait_until

REGISTRATION_DATA = {
    "event_id": 12,
    "event_title": "Хакатон",
    "participant_id": 5,
    "participant_name": "Иван Петров",
}
EVENT_DATA = {
    "event_id": 12,
    "event_title": "Хакатон",
    "event_date": "2026-12-01T18:30:00Z",
    "location": "Аудитория 101",
    "changed_fields": ["location"],
}


def body(
    *,
    message_id: UUID | None = None,
    event_type: str = "registration.created",
    data: dict[str, Any] | None = None,
) -> bytes:
    return json.dumps({
        "message_id": str(message_id or uuid4()),
        "event_id": str(uuid4()),
        "type": event_type,
        "occurred_at": "2026-11-20T12:00:00Z",
        "recipient_ids": [7],
        "data": data if data is not None else REGISTRATION_DATA,
    }).encode()


async def notifications_count(session_maker: async_sessionmaker[AsyncSession]) -> int:
    async with session_maker() as session:
        return await session.scalar(select(func.count()).select_from(Notification))


async def ready_messages(connection: AbstractConnection, queue_name: str) -> int:
    """Сколько сообщений ждёт в очереди (неподтверждённые после закрытия канала
    consumer'а возвращаются в очередь и тоже попадают в это число)."""
    channel = await connection.channel()
    queue = await channel.declare_queue(queue_name, passive=True)
    count = queue.declaration_result.message_count
    await channel.close()
    return count


@pytest.mark.parametrize(
    ("routing_key", "data"),
    [("registration.created", REGISTRATION_DATA), ("event.updated", EVENT_DATA)],
    ids=["registration.*", "event.*"],
)
async def test_message_is_saved_and_acked(
    consumer: AbstractChannel,
    publish: Publish,
    rabbit_connection: AbstractConnection,
    rabbitmq_settings: RabbitMQSettings,
    session_maker,
    routing_key: str,
    data: dict[str, Any],
):
    await publish(body(event_type=routing_key, data=data), routing_key)

    async def saved() -> bool:
        return await notifications_count(session_maker) == 1

    await wait_until(saved)
    await consumer.close()
    assert await ready_messages(rabbit_connection, rabbitmq_settings.queue) == 0


async def test_duplicate_message_is_acked_without_new_notification(
    consumer: AbstractChannel,
    publish: Publish,
    rabbit_connection: AbstractConnection,
    rabbitmq_settings: RabbitMQSettings,
    session_maker,
):
    message = body()
    await publish(message)
    await publish(message)

    async def saved() -> bool:
        return await notifications_count(session_maker) == 1

    await wait_until(saved)
    await asyncio.sleep(0.5)  # даём consumer'у разобрать второе сообщение
    await consumer.close()

    assert await notifications_count(session_maker) == 1
    assert await ready_messages(rabbit_connection, rabbitmq_settings.queue) == 0


async def test_invalid_message_goes_to_dead_letter_queue(
    consumer: AbstractChannel,
    publish: Publish,
    rabbit_connection: AbstractConnection,
    rabbitmq_settings: RabbitMQSettings,
    session_maker,
):
    await publish(b"not json")

    async def dead_lettered() -> bool:
        return await ready_messages(rabbit_connection, rabbitmq_settings.dead_letter_queue) == 1

    await wait_until(dead_lettered)
    assert await notifications_count(session_maker) == 0


async def test_failed_processing_is_retried(
    publish: Publish,
    rabbit_connection: AbstractConnection,
    rabbitmq_settings: RabbitMQSettings,
    session_maker: async_sessionmaker[AsyncSession],
):
    attempts = 0

    def flaky_session_factory() -> AsyncSession:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ConnectionError("db is down")
        return session_maker()

    channel = await start_consumer(
        rabbit_connection,
        rabbitmq_settings,
        session_factory=flaky_session_factory,
    )
    await publish(body())

    async def saved() -> bool:
        return await notifications_count(session_maker) == 1

    await wait_until(saved)
    await channel.close()
    assert attempts >= 2


async def test_saved_notification_is_pushed_to_online_user(
    publish: Publish,
    rabbit_connection: AbstractConnection,
    rabbitmq_settings: RabbitMQSettings,
    session_maker: async_sessionmaker[AsyncSession],
):
    manager = ConnectionManager()
    websocket = FakeWebSocket()
    manager.connect(7, websocket)
    channel = await start_consumer(
        rabbit_connection,
        rabbitmq_settings,
        session_factory=session_maker,
        manager=manager,
    )

    await publish(body())

    async def pushed() -> bool:
        return len(websocket.sent) == 1

    await wait_until(pushed)
    await channel.close()
    assert websocket.sent[0]["title"] == "Новая запись на мероприятие"
