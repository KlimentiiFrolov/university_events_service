import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.uow import UnitOfWork
from src.events.types import DomainEventType
from src.models.outbox import OutboxMessage
from src.outbox.relay import dispatch, process_batch, save_results

PAYLOAD = {"event_id": 1, "user_id": 2}


class FakeBus:
    """Шина вместо event_bus: записывает вызовы, умеет падать и считает параллельные вызовы."""

    def __init__(self) -> None:
        self.calls: list[tuple[DomainEventType, dict[str, Any], UUID | None, datetime | None]] = []
        self.fail = False
        self.running = 0
        self.max_running = 0

    async def publish(self, event_type, payload, *, event_id=None, occurred_at=None) -> None:
        self.running += 1
        self.max_running = max(self.max_running, self.running)
        try:
            await asyncio.sleep(0.01)
            if self.fail:
                raise RuntimeError("handler failed")
            self.calls.append((event_type, payload, event_id, occurred_at))
        finally:
            self.running -= 1


type AddOutboxMessage = Callable[..., Awaitable[OutboxMessage]]


@pytest.fixture
def bus() -> FakeBus:
    return FakeBus()


@pytest.fixture
def uow_factory(session_maker: async_sessionmaker[AsyncSession]) -> Callable[[], UnitOfWork]:
    return lambda: UnitOfWork(session_factory=session_maker)


@pytest.fixture
def add_outbox_message(uow: UnitOfWork) -> AddOutboxMessage:
    async def _add(routing_key: str = DomainEventType.REGISTRATION_CREATED) -> OutboxMessage:
        message = await uow.outbox.add(OutboxMessage(routing_key=routing_key, payload=PAYLOAD))
        await uow.commit()
        return message

    return _add


async def stored(session_maker: async_sessionmaker[AsyncSession], message_id: UUID) -> OutboxMessage:
    async with session_maker() as session:
        message = await session.scalar(select(OutboxMessage).where(OutboxMessage.id == message_id))
        assert message is not None
        return message


def in_memory_message(routing_key: str = DomainEventType.REGISTRATION_CREATED) -> OutboxMessage:
    return OutboxMessage(
        id=uuid4(),
        routing_key=routing_key,
        payload=PAYLOAD,
        created_at=datetime(2026, 11, 20, 12, 0, tzinfo=UTC),
    )


# --- process_batch ---


async def test_publishes_event_and_marks_it(
    bus: FakeBus,
    uow_factory,
    session_maker,
    add_outbox_message: AddOutboxMessage,
):
    message = await add_outbox_message()

    processed = await process_batch(10, 5, bus=bus, uow_factory=uow_factory)

    assert processed == 1
    assert bus.calls == [(
        DomainEventType.REGISTRATION_CREATED,
        PAYLOAD,
        message.id,
        message.created_at,
    )]
    assert (await stored(session_maker, message.id)).published_at is not None


async def test_published_event_is_not_processed_again(
    bus: FakeBus,
    uow_factory,
    add_outbox_message: AddOutboxMessage,
):
    await add_outbox_message()
    await process_batch(10, 5, bus=bus, uow_factory=uow_factory)

    processed = await process_batch(10, 5, bus=bus, uow_factory=uow_factory)

    assert processed == 0
    assert len(bus.calls) == 1


async def test_failed_event_stays_unpublished(
    bus: FakeBus,
    uow_factory,
    session_maker,
    add_outbox_message: AddOutboxMessage,
):
    message = await add_outbox_message()
    bus.fail = True

    await process_batch(10, 5, bus=bus, uow_factory=uow_factory)

    failed = await stored(session_maker, message.id)
    assert failed.published_at is None
    assert failed.attempts == 1
    assert "handler failed" in failed.last_error


async def test_failed_event_is_retried_with_same_event_id(
    bus: FakeBus,
    uow_factory,
    session_maker,
    add_outbox_message: AddOutboxMessage,
):
    message = await add_outbox_message()
    bus.fail = True
    await process_batch(10, 5, bus=bus, uow_factory=uow_factory)
    bus.fail = False

    await process_batch(10, 5, bus=bus, uow_factory=uow_factory)

    assert len(bus.calls) == 1
    _, _, event_id, _ = bus.calls[0]
    assert event_id == message.id
    assert (await stored(session_maker, message.id)).published_at is not None


async def test_unknown_event_type_is_marked_failed(
    bus: FakeBus,
    uow_factory,
    session_maker,
    add_outbox_message: AddOutboxMessage,
):
    message = await add_outbox_message("unknown.type")

    await process_batch(10, 5, bus=bus, uow_factory=uow_factory)

    failed = await stored(session_maker, message.id)
    assert failed.published_at is None
    assert failed.attempts == 1
    assert bus.calls == []


async def test_respects_batch_size(
    bus: FakeBus,
    uow_factory,
    add_outbox_message: AddOutboxMessage,
):
    await add_outbox_message()
    await add_outbox_message()

    processed = await process_batch(1, 5, bus=bus, uow_factory=uow_factory)

    assert processed == 1
    assert len(bus.calls) == 1


async def test_failed_event_does_not_block_others_in_batch(
    bus: FakeBus,
    uow_factory,
    session_maker,
    add_outbox_message: AddOutboxMessage,
):
    broken = await add_outbox_message("unknown.type")
    valid = await add_outbox_message()

    processed = await process_batch(10, 5, bus=bus, uow_factory=uow_factory)

    assert processed == 2
    assert len(bus.calls) == 1
    assert (await stored(session_maker, valid.id)).published_at is not None
    assert (await stored(session_maker, broken.id)).attempts == 1


# --- dispatch ---


async def test_dispatch_passes_row_id_and_time_to_bus(bus: FakeBus):
    message = in_memory_message()

    await dispatch(message, asyncio.Semaphore(1), bus)

    assert bus.calls == [(
        DomainEventType.REGISTRATION_CREATED,
        PAYLOAD,
        message.id,
        message.created_at,
    )]


async def test_dispatch_rejects_unknown_event_type(bus: FakeBus):
    with pytest.raises(ValueError):
        await dispatch(in_memory_message("unknown.type"), asyncio.Semaphore(1), bus)

    assert bus.calls == []


async def test_dispatch_respects_semaphore_limit(bus: FakeBus):
    semaphore = asyncio.Semaphore(2)

    await asyncio.gather(*(dispatch(in_memory_message(), semaphore, bus) for _ in range(5)))

    assert len(bus.calls) == 5
    assert bus.max_running == 2


# --- save_results ---


async def test_save_results_marks_published_and_failed(
    session_maker,
    uow: UnitOfWork,
    add_outbox_message: AddOutboxMessage,
):
    ok = await add_outbox_message()
    broken = await add_outbox_message()

    published = await save_results(uow, [ok, broken], [None, RuntimeError("handler failed")])
    await uow.commit()

    assert published == 1
    assert (await stored(session_maker, ok.id)).published_at is not None
    failed = await stored(session_maker, broken.id)
    assert failed.published_at is None
    assert failed.attempts == 1
    assert "handler failed" in failed.last_error


async def test_save_results_with_empty_batch_returns_zero(uow: UnitOfWork):
    assert await save_results(uow, [], []) == 0
