"""JSON contract of /ws/notifications, matching NotificationPayload on the server."""

from collections import deque
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class NotificationPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["notification"]
    id: int = Field(gt=0)
    event_type: str
    title: str
    text: str
    data: dict[str, Any]
    created_at: datetime


def format_notification(message: NotificationPayload) -> str:
    """Make a readable console line from a validated notification."""
    date = message.created_at.astimezone().strftime("%d.%m.%Y %H:%M:%S")
    return (
        f"[{date}] {message.title}\n"
        f"  {message.text}\n"
        f"  Уведомление #{message.id} · {message.event_type}"
    )


class RecentNotificationIds:
    """Suppress duplicates across reconnects, without growing memory forever."""

    def __init__(self, capacity: int = 1000):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._ids: set[int] = set()
        self._ordered: deque[int] = deque()
        self._capacity = capacity

    def is_new(self, message_id: int) -> bool:
        if message_id in self._ids:
            return False
        if len(self._ordered) == self._capacity:
            self._ids.remove(self._ordered.popleft())
        self._ordered.append(message_id)
        self._ids.add(message_id)
        return True
