from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

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
        *,
        event_id: UUID | None = None,
        occurred_at: datetime | None = None,
    ) -> DomainEvent:
        """Собрать событие и передать его обработчикам.

        Relay передаёт event_id и occurred_at из строки outbox: при повторной обработке
        той же строки событие получает тот же id.
        """
        event = DomainEvent(
            id=event_id or uuid4(),
            type=event_type,
            occurred_at=occurred_at or get_current_datetime(),
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

    def register(self, *event_types: DomainEventType):
        def decorator(func: EventHandler):
            for event_type in event_types:
                self.subscribe(event_type, func)

            return func

        return decorator

