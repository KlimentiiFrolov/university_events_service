import json
from uuid import UUID, uuid4, uuid5

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.uow import UnitOfWork
from src.events import DomainEventType, EventBus
from src.events.handlers import NOTIFICATIONS_CHANNEL, event_bus
from src.schemas.messages import NotificationMessage
from src.services.events import EventService
from src.services.registrations import RegistrationService


class FakePublisher:
    def __init__(self) -> None:
        self.published: list[tuple[str, NotificationMessage, UUID]] = []

    async def publish(self, routing_key: str, body: bytes, message_id: UUID) -> None:
        message = NotificationMessage.model_validate(json.loads(body))
        self.published.append((routing_key, message, message_id))


@pytest.fixture
def publisher(monkeypatch: pytest.MonkeyPatch) -> FakePublisher:
    fake = FakePublisher()
    monkeypatch.setattr("src.events.handlers.rabbit_publisher", fake)
    return fake


@pytest.fixture
def bus(
    monkeypatch: pytest.MonkeyPatch,
    session_maker: async_sessionmaker[AsyncSession],
    publisher: FakePublisher,
) -> EventBus:
    """Шина приложения, но обработчики ходят в тестовую БД и фейковый брокер."""
    monkeypatch.setattr(
        "src.events.handlers.UnitOfWork",
        lambda: UnitOfWork(session_factory=session_maker),
    )
    return event_bus


def single_message(publisher: FakePublisher) -> tuple[str, NotificationMessage, UUID]:
    assert len(publisher.published) == 1
    return publisher.published[0]


@pytest.mark.parametrize(
    "event_type",
    [DomainEventType.REGISTRATION_CREATED, DomainEventType.REGISTRATION_CANCELLED],
)
async def test_registration_notifies_organizer(
    bus: EventBus,
    publisher: FakePublisher,
    make_event,
    make_user,
    event_type: DomainEventType,
):
    event = await make_event(title="Hackathon")
    participant = await make_user(first_name="Ivan", second_name="Petrov")

    occurred = await bus.publish(event_type, {"event_id": event.id, "user_id": participant.id})

    routing_key, message, message_id = single_message(publisher)
    assert routing_key == event_type
    assert message_id == message.message_id == uuid5(occurred.id, NOTIFICATIONS_CHANNEL)
    assert message.event_id == occurred.id
    assert message.type == event_type
    assert message.recipient_ids == [event.created_by_id]
    assert message.data == {
        "event_id": event.id,
        "event_title": "Hackathon",
        "participant_id": participant.id,
        "participant_name": "Ivan Petrov",
    }


async def test_same_event_id_gives_same_message_id(
    bus: EventBus,
    publisher: FakePublisher,
    make_event,
    make_user,
):
    event = await make_event()
    participant = await make_user()
    payload = {"event_id": event.id, "user_id": participant.id}
    event_id = uuid4()

    await bus.publish(DomainEventType.REGISTRATION_CREATED, payload, event_id=event_id)
    await bus.publish(DomainEventType.REGISTRATION_CREATED, payload, event_id=event_id)

    first_id = publisher.published[0][2]
    second_id = publisher.published[1][2]
    assert first_id == second_id


async def test_event_updated_notifies_only_active_participants(
    bus: EventBus,
    publisher: FakePublisher,
    uow: UnitOfWork,
    registration_service: RegistrationService,
    make_event,
    make_user,
):
    event = await make_event()
    first = await make_user()
    second = await make_user()
    left = await make_user()
    for user in (first, second, left):
        await registration_service.register(user.id, event.id)
    await registration_service.cancel(left.id, event.id)
    await uow.commit()

    await bus.publish(
        DomainEventType.EVENT_UPDATED,
        {"event_id": event.id, "changed_fields": ["location"]},
    )

    _, message, _ = single_message(publisher)
    assert sorted(message.recipient_ids) == sorted([first.id, second.id])
    assert message.data["changed_fields"] == ["location"]
    assert message.data["location"] == event.location


async def test_event_updated_without_participants_publishes_nothing(
    bus: EventBus,
    publisher: FakePublisher,
    make_event,
):
    event = await make_event()

    await bus.publish(
        DomainEventType.EVENT_UPDATED,
        {"event_id": event.id, "changed_fields": ["title"]},
    )

    assert publisher.published == []


async def test_event_cancelled_notifies_participants_of_deleted_event(
    bus: EventBus,
    publisher: FakePublisher,
    uow: UnitOfWork,
    event_service: EventService,
    registration_service: RegistrationService,
    make_event,
    make_user,
):
    event = await make_event(title="Lecture")
    participant = await make_user()
    await registration_service.register(participant.id, event.id)
    participant_ids = await event_service.delete_event(event.id, event.created_by_id)
    await uow.commit()

    await bus.publish(
        DomainEventType.EVENT_CANCELLED,
        {"event_id": event.id, "participant_ids": participant_ids},
    )

    _, message, _ = single_message(publisher)
    assert message.recipient_ids == [participant.id]
    assert message.data["event_title"] == "Lecture"


async def test_missing_event_is_skipped(
    bus: EventBus,
    publisher: FakePublisher,
    make_user,
):
    participant = await make_user()

    await bus.publish(
        DomainEventType.REGISTRATION_CREATED,
        {"event_id": 999_999, "user_id": participant.id},
    )

    assert publisher.published == []


async def test_invalid_payload_raises_validation_error(bus: EventBus):
    with pytest.raises(ValidationError):
        await bus.publish(DomainEventType.REGISTRATION_CREATED, {"event_id": 1})
