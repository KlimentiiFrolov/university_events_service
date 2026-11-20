import json
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from notifications.models import InboxMessage, Notification
from notifications.services.message_processor import ProcessStatus, process_message

REGISTRATION_DATA = {
    "event_id": 12,
    "event_title": "Хакатон",
    "participant_id": 5,
    "participant_name": "Иван Петров",
}


def body(
    *,
    message_id: UUID | None = None,
    event_type: str = "registration.created",
    recipient_ids: list[int] | None = None,
    data: dict[str, Any] | None = None,
) -> bytes:
    return json.dumps({
        "message_id": str(message_id or uuid4()),
        "event_id": str(uuid4()),
        "type": event_type,
        "occurred_at": "2026-11-20T12:00:00Z",
        "recipient_ids": recipient_ids if recipient_ids is not None else [7],
        "data": data if data is not None else REGISTRATION_DATA,
    }).encode()


async def count(session_maker: async_sessionmaker[AsyncSession], model) -> int:
    async with session_maker() as session:
        return await session.scalar(select(func.count()).select_from(model))


async def test_new_message_saves_notification_per_recipient(session_maker):
    message_id = uuid4()

    result = await process_message(
        body(message_id=message_id, recipient_ids=[7, 8]),
        session_factory=session_maker,
    )

    assert result.status == ProcessStatus.PROCESSED
    assert sorted(notification.user_id for notification in result.notifications) == [7, 8]
    notification = result.notifications[0]
    assert notification.message_id == message_id
    assert notification.title == "Новая запись на мероприятие"
    assert notification.data == REGISTRATION_DATA
    assert await count(session_maker, Notification) == 2
    assert await count(session_maker, InboxMessage) == 1


async def test_saved_notification_is_usable_after_session_closed(session_maker):
    result = await process_message(body(), session_factory=session_maker)

    notification = result.notifications[0]
    assert notification.id is not None
    assert notification.created_at is not None
    assert notification.delivered_at is None


async def test_repeated_message_is_duplicate(session_maker):
    message = body()
    await process_message(message, session_factory=session_maker)

    result = await process_message(message, session_factory=session_maker)

    assert result.status == ProcessStatus.DUPLICATE
    assert result.notifications == []
    assert await count(session_maker, Notification) == 1


@pytest.mark.parametrize(
    "invalid_body",
    [
        b"not json",
        body(event_type="unknown.type"),
        body(data={"event_id": 12}),
    ],
    ids=["not json", "unknown type", "invalid data"],
)
async def test_invalid_message_saves_nothing(session_maker, invalid_body: bytes):
    result = await process_message(invalid_body, session_factory=session_maker)

    assert result.status == ProcessStatus.INVALID
    assert await count(session_maker, InboxMessage) == 0
    assert await count(session_maker, Notification) == 0
