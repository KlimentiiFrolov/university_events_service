"""Сообщения, которые api_service отправляет в RabbitMQ.

Копия схемы живёт в notification_service; совместимость проверяет контрактный тест.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from src.events.types import DomainEventType


class NotificationMessage(BaseModel):
    message_id: UUID
    event_id: UUID
    type: DomainEventType
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
