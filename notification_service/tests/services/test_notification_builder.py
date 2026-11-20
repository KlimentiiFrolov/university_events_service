from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from notifications.schemas.messages import EventType, NotificationMessage
from notifications.services.notification_builder import build_notification

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
}


def message(event_type: EventType, data: dict[str, Any]) -> NotificationMessage:
    return NotificationMessage(
        message_id=uuid4(),
        event_id=uuid4(),
        type=event_type,
        occurred_at=datetime(2026, 11, 20, 12, 0, tzinfo=UTC),
        recipient_ids=[1],
        data=data,
    )


def test_registration_created():
    content = build_notification(message(EventType.REGISTRATION_CREATED, REGISTRATION_DATA))

    assert content.title == "Новая запись на мероприятие"
    assert content.text == "Иван Петров записался(-ась) на «Хакатон»."


def test_registration_cancelled():
    content = build_notification(message(EventType.REGISTRATION_CANCELLED, REGISTRATION_DATA))

    assert content.title == "Отмена записи на мероприятие"
    assert content.text == "Иван Петров отменил(а) запись на «Хакатон»."


def test_event_updated_lists_changed_fields():
    data = {**EVENT_DATA, "changed_fields": ["location", "event_date"]}

    content = build_notification(message(EventType.EVENT_UPDATED, data))

    assert content.title == "Мероприятие изменено"
    assert content.text == (
        "В мероприятии «Хакатон» изменено: место, дата. "
        "Сейчас: 01.12.2026 18:30, Аудитория 101."
    )


def test_event_updated_keeps_unknown_field_name():
    data = {**EVENT_DATA, "changed_fields": ["new_field"]}

    content = build_notification(message(EventType.EVENT_UPDATED, data))

    assert "изменено: new_field." in content.text


def test_event_cancelled():
    content = build_notification(message(EventType.EVENT_CANCELLED, EVENT_DATA))

    assert content.title == "Мероприятие отменено"
    assert content.text == "Мероприятие «Хакатон» (01.12.2026 18:30, Аудитория 101) отменено."


def test_invalid_data_raises_validation_error():
    with pytest.raises(ValidationError):
        build_notification(message(EventType.REGISTRATION_CREATED, {"event_id": 12}))


def test_unknown_event_type_is_rejected_by_schema():
    with pytest.raises(ValidationError):
        NotificationMessage.model_validate({
            "message_id": str(uuid4()),
            "event_id": str(uuid4()),
            "type": "unknown.type",
            "occurred_at": "2026-11-20T12:00:00Z",
            "recipient_ids": [1],
            "data": {},
        })
