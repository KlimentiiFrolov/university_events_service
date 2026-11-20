from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.events import DomainEvent, DomainEventType, EventBus

FIXED_NOW = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
PAYLOAD = {"event_id": 12, "user_id": 5}


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
def calls() -> list[tuple[str, DomainEvent]]:
    return []


def recording_handler(name: str, calls: list):
    async def handler(event: DomainEvent) -> None:
        calls.append((name, event))

    return handler


async def test_publish_calls_handlers_in_subscription_order(bus, calls):
    bus.subscribe(DomainEventType.REGISTRATION_CREATED, recording_handler("first", calls))
    bus.subscribe(DomainEventType.REGISTRATION_CREATED, recording_handler("second", calls))

    event = await bus.publish(DomainEventType.REGISTRATION_CREATED, PAYLOAD)

    assert [name for name, _ in calls] == ["first", "second"]
    assert all(received is event for _, received in calls)


async def test_publish_calls_only_handlers_of_its_type(bus, calls):
    bus.subscribe(DomainEventType.REGISTRATION_CREATED, recording_handler("created", calls))
    bus.subscribe(DomainEventType.EVENT_CANCELLED, recording_handler("cancelled", calls))

    await bus.publish(DomainEventType.EVENT_CANCELLED, PAYLOAD)

    assert len(calls) == 1
    name, _ = calls[0]
    assert name == "cancelled"


async def test_publish_without_handlers_returns_event(bus):
    event = await bus.publish(DomainEventType.EVENT_UPDATED, PAYLOAD)

    assert event.type == DomainEventType.EVENT_UPDATED


async def test_publish_builds_event(bus, monkeypatch):
    monkeypatch.setattr("src.events.bus.get_current_datetime", lambda: FIXED_NOW)

    event = await bus.publish(DomainEventType.REGISTRATION_CANCELLED, PAYLOAD)

    assert event.type == DomainEventType.REGISTRATION_CANCELLED
    assert event.payload == PAYLOAD
    assert event.occurred_at == FIXED_NOW


async def test_publish_uses_given_id_and_time(bus):
    event_id = uuid4()

    event = await bus.publish(
        DomainEventType.EVENT_UPDATED,
        PAYLOAD,
        event_id=event_id,
        occurred_at=FIXED_NOW,
    )

    assert event.id == event_id
    assert event.occurred_at == FIXED_NOW


async def test_publish_generates_unique_ids(bus):
    first = await bus.publish(DomainEventType.EVENT_UPDATED, PAYLOAD)
    second = await bus.publish(DomainEventType.EVENT_UPDATED, PAYLOAD)

    assert first.id != second.id


async def test_handler_error_propagates_and_stops_chain(bus, calls):
    async def failing_handler(event: DomainEvent) -> None:
        raise RuntimeError("handler failed")

    bus.subscribe(DomainEventType.REGISTRATION_CREATED, failing_handler)
    bus.subscribe(DomainEventType.REGISTRATION_CREATED, recording_handler("after", calls))

    with pytest.raises(RuntimeError, match="handler failed"):
        await bus.publish(DomainEventType.REGISTRATION_CREATED, PAYLOAD)

    assert calls == []


async def test_domain_event_is_immutable(bus):
    event = await bus.publish(DomainEventType.EVENT_UPDATED, PAYLOAD)

    with pytest.raises(ValidationError):
        event.type = DomainEventType.EVENT_CANCELLED
