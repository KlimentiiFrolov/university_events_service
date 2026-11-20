import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.clients.rabbitmq import RabbitPublisher
from src.core.config import OutboxSettings
from src.core.uow import UnitOfWork
from src.events.bus import EventBus
from src.events.types import DomainEvent, DomainEventType
from src.models.outbox import OutboxMessage
from src.outbox.relay import dispatch, process_batch, run_relay, save_results

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
    assert failed.last_error is not None
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
    assert failed.last_error is not None
    assert "handler failed" in failed.last_error


async def test_save_results_with_empty_batch_returns_zero(uow: UnitOfWork):
    assert await save_results(uow, [], []) == 0


# --- run_relay ---


def relay_config(*, poll_interval: float = 0.05, batch_size: int = 10) -> OutboxSettings:
    return OutboxSettings.model_construct(
        relay_enabled=True,
        poll_interval=poll_interval,
        batch_size=batch_size,
        concurrency=5,
    )


async def wait_until(condition: Callable[[], Awaitable[bool]], timeout: float = 5.0) -> None:
    async def _poll() -> None:
        while not await condition():
            await asyncio.sleep(0.01)

    await asyncio.wait_for(_poll(), timeout)


async def test_run_relay_processes_events_until_stopped(
    bus: FakeBus,
    uow_factory,
    session_maker,
    add_outbox_message: AddOutboxMessage,
):
    message = await add_outbox_message()
    stop = asyncio.Event()
    task = asyncio.create_task(
        run_relay(stop, relay_config(), bus=bus, uow_factory=uow_factory)
    )

    async def is_published() -> bool:
        return (await stored(session_maker, message.id)).published_at is not None

    await wait_until(is_published)
    stop.set()
    await asyncio.wait_for(task, timeout=1)


async def test_run_relay_stops_after_current_pause(bus: FakeBus, uow_factory):
    stop = asyncio.Event()
    task = asyncio.create_task(
        run_relay(stop, relay_config(poll_interval=0.05), bus=bus, uow_factory=uow_factory)
    )
    await asyncio.sleep(0.05)

    stop.set()

    await asyncio.wait_for(task, timeout=1)


async def test_run_relay_takes_next_full_batch_without_waiting(
    bus: FakeBus,
    uow_factory,
    add_outbox_message: AddOutboxMessage,
):
    await add_outbox_message()
    await add_outbox_message()
    stop = asyncio.Event()
    # Пауза больше таймаута ожидания: оба события успеют уйти, только если паузы между
    # полными пачками нет
    config = relay_config(poll_interval=0.5, batch_size=1)
    task = asyncio.create_task(run_relay(stop, config, bus=bus, uow_factory=uow_factory))

    async def both_sent() -> bool:
        return len(bus.calls) == 2

    await wait_until(both_sent, timeout=0.3)
    stop.set()
    await asyncio.wait_for(task, timeout=1)


async def test_run_relay_survives_iteration_error(
    bus: FakeBus,
    uow_factory,
    session_maker,
    add_outbox_message: AddOutboxMessage,
):
    message = await add_outbox_message()
    attempts = 0

    def flaky_uow_factory() -> UnitOfWork:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ConnectionError("db is down")
        return uow_factory()

    stop = asyncio.Event()
    task = asyncio.create_task(
        run_relay(stop, relay_config(poll_interval=0.01), bus=bus, uow_factory=flaky_uow_factory)
    )

    async def is_published() -> bool:
        return (await stored(session_maker, message.id)).published_at is not None

    await wait_until(is_published)
    stop.set()
    await asyncio.wait_for(task, timeout=1)
    assert attempts >= 2


# --- relay + RabbitMQ ---


@pytest.fixture
def rabbit_bus(rabbit_publisher: RabbitPublisher) -> EventBus:
    """Шина с одним обработчиком, который отправляет событие в настоящий RabbitMQ."""
    bus = EventBus()

    @bus.register(DomainEventType.REGISTRATION_CREATED)
    async def send(event: DomainEvent) -> None:
        await rabbit_publisher.publish(
            routing_key=event.type,
            body=event.model_dump_json().encode(),
            message_id=event.id,
        )

    return bus


async def test_relay_delivers_outbox_event_to_rabbitmq(
    rabbit_bus: EventBus,
    uow_factory,
    session_maker,
    add_outbox_message: AddOutboxMessage,
    receive_message,
):
    outbox_message = await add_outbox_message()

    await process_batch(10, 5, bus=rabbit_bus, uow_factory=uow_factory)

    received = await receive_message()
    assert received.routing_key == DomainEventType.REGISTRATION_CREATED
    assert received.message_id == str(outbox_message.id)
    assert DomainEvent.model_validate_json(received.body).payload == PAYLOAD
    assert (await stored(session_maker, outbox_message.id)).published_at is not None


async def test_relay_keeps_event_when_broker_is_unavailable(
    rabbit_bus: EventBus,
    rabbit_publisher: RabbitPublisher,
    uow_factory,
    session_maker,
    add_outbox_message: AddOutboxMessage,
):
    outbox_message = await add_outbox_message()
    await rabbit_publisher.close()

    await process_batch(10, 5, bus=rabbit_bus, uow_factory=uow_factory)

    failed = await stored(session_maker, outbox_message.id)
    assert failed.published_at is None
    assert failed.attempts == 1
