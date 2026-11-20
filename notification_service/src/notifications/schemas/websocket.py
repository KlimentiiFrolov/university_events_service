"""Протокол WebSocket между сервисом и клиентом."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from notifications.models import Notification


class NotificationPayload(BaseModel):
    """Сервер -> клиент: уведомление."""

    type: Literal["notification"] = "notification"
    id: int
    event_type: str
    title: str
    text: str
    data: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_model(cls, notification: Notification) -> "NotificationPayload":
        return cls(
            id=notification.id,
            event_type=notification.type,
            title=notification.title,
            text=notification.text,
            data=notification.data,
            created_at=notification.created_at,
        )

