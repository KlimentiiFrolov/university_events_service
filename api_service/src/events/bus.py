from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from src.core.dates import get_current_datetime
from src.core.logger import log

from .types import DomainEvent, DomainEventType

type EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: defaultdict[DomainEventType, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: DomainEventType, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(
        self,
        event_type: DomainEventType,
        payload: dict[str, Any],
    ) -> DomainEvent:
        event = DomainEvent(
            id=uuid4(),
            type=event_type,
            occurred_at=get_current_datetime(),
            payload=payload,
        )

        handlers = self._handlers.get(event_type, [])
        log.debug(
            "Publishing domain event %s id=%s to %d handler(s)",
            event.type, event.id, len(handlers),
        )

        for handler in handlers:
            await handler(event)

        return event
