"""Сообщения, которые api_service присылает через RabbitMQ.

Копия схемы из api_service (src/schemas/messages.py): сервисы не делят код,
совместимость проверяется тестами.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class EventType(StrEnum):
    REGISTRATION_CREATED = "registration.created"
    REGISTRATION_CANCELLED = "registration.cancelled"
    EVENT_UPDATED = "event.updated"
    EVENT_CANCELLED = "event.cancelled"


class NotificationMessage(BaseModel):
    message_id: UUID
    event_id: UUID
    type: EventType
    occurred_at: datetime
    recipient_ids: list[int]
    data: dict[str, Any]


class RegistrationNotificationData(BaseModel):
    """'data' для 'registration.*': получатель - организатор мероприятия."""

    event_id: int
    event_title: str
    participant_id: int
    participant_name: str


class EventNotificationData(BaseModel):
    """'data' для 'event.*': получатели - участники мероприятия."""

    event_id: int
    event_title: str
    event_date: datetime
    location: str
    changed_fields: list[str] = []
