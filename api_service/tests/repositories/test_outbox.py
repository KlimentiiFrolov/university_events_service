from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.uow import UnitOfWork
from src.events.payloads import RegistrationCreatedPayload
from src.events.types import DomainEventType
from src.models.outbox import OutboxMessage
from src.repositories.outbox import OutboxRepository

BASE_TIME = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)

type MakeMessage = Callable[..., Awaitable[OutboxMessage]]


@pytest.fixture
def make_message(uow: UnitOfWork) -> MakeMessage:
    async def _make_message(
        *,
        routing_key: str = "registration.created",
        created_at: datetime = BASE_TIME,
    ) -> OutboxMessage:
        message = await uow.outbox.add(
            OutboxMessage(
                routing_key=routing_key,
                payload={"recipient_ids": [1]},
                created_at=created_at,
            )
        )
        await uow.commit()

        return message

    return _make_message


async def test_add_assigns_defaults(make_message: MakeMessage):
    message = await make_message()

    assert message.id is not None
    assert message.attempts == 0
    assert message.published_at is None
    assert message.last_error is None


async def test_add_event_stores_type_and_payload(uow: UnitOfWork):
    message = await uow.outbox.add_event(
        DomainEventType.REGISTRATION_CREATED,
        RegistrationCreatedPayload(event_id=12, user_id=5),
    )

    assert message.id is not None
    assert message.created_at is not None
    assert message.routing_key == DomainEventType.REGISTRATION_CREATED
    assert message.payload == {"event_id": 12, "user_id": 5}
    assert message.published_at is None


async def test_fetch_returns_unpublished_in_creation_order(
    uow: UnitOfWork,
    make_message: MakeMessage,
):
    later = await make_message(created_at=BASE_TIME + timedelta(seconds=2))
    earlier = await make_message(created_at=BASE_TIME)
    published = await make_message(created_at=BASE_TIME + timedelta(seconds=1))
    await uow.outbox.mark_published([published.id])
    await uow.commit()

    messages = await uow.outbox.fetch_unpublished_for_update(limit=10)

    assert [message.id for message in messages] == [earlier.id, later.id]


async def test_fetch_respects_limit(uow: UnitOfWork, make_message: MakeMessage):
    first = await make_message(created_at=BASE_TIME)
    await make_message(created_at=BASE_TIME + timedelta(seconds=1))

    messages = await uow.outbox.fetch_unpublished_for_update(limit=1)

    assert [message.id for message in messages] == [first.id]


async def test_mark_published_sets_published_at(
    uow: UnitOfWork,
    make_message: MakeMessage,
):
    message = await make_message()

    await uow.outbox.mark_published([message.id])
    await uow.session.refresh(message)

    assert message.published_at is not None


async def test_mark_published_with_empty_list_does_nothing(
    uow: UnitOfWork,
    make_message: MakeMessage,
):
    message = await make_message()

    await uow.outbox.mark_published([])
    await uow.session.refresh(message)

    assert message.published_at is None


async def test_mark_failed_counts_attempts_and_keeps_message_unpublished(
    uow: UnitOfWork,
    make_message: MakeMessage,
):
    message = await make_message()

    await uow.outbox.mark_failed(message.id, "broker is down")
    await uow.outbox.mark_failed(message.id, "still down")
    await uow.session.refresh(message)

    assert message.attempts == 2
    assert message.last_error == "still down"
    assert message.published_at is None


async def test_fetch_skips_rows_locked_by_another_transaction(
    session_maker: async_sessionmaker[AsyncSession],
    make_message: MakeMessage,
):
    locked = await make_message(created_at=BASE_TIME)
    free = await make_message(created_at=BASE_TIME + timedelta(seconds=1))

    async with session_maker() as first_session, session_maker() as second_session:
        first_batch = await OutboxRepository(first_session).fetch_unpublished_for_update(limit=1)
        second_batch = await OutboxRepository(second_session).fetch_unpublished_for_update(limit=10)

        assert [message.id for message in first_batch] == [locked.id]
        assert [message.id for message in second_batch] == [free.id]
