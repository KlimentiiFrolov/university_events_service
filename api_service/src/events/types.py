from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DomainEventType(StrEnum):
    """Значимые события предметной области. Значение — routing key в RabbitMQ."""

    REGISTRATION_CREATED = "registration.created"
    REGISTRATION_CANCELLED = "registration.cancelled"
    EVENT_UPDATED = "event.updated"
    EVENT_CANCELLED = "event.cancelled"


class DomainEvent(BaseModel):
    """Факт, который произошёл в api_service и на который реагируют обработчики шины."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    type: DomainEventType
    occurred_at: datetime
    payload: dict[str, Any]
