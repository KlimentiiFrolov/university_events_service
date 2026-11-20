"""Relay: читает неотправленные доменные события из outbox и передаёт их в event_bus.

Не зависит от FastAPI: запускается из lifespan api_service или отдельным процессом.
"""

import asyncio
from collections.abc import Callable

from src.core.logger import log
from src.core.uow import UnitOfWork
from src.events.bus import EventBus
from src.events.handlers import event_bus
from src.events.types import DomainEventType
from src.models.outbox import OutboxMessage


async def dispatch(
    message: OutboxMessage,
    semaphore: asyncio.Semaphore,
    bus: EventBus,
) -> None:
    """Передать событие из outbox обработчикам шины."""
    async with semaphore:
        await bus.publish(
            DomainEventType(message.routing_key),
            message.payload,
            event_id=message.id,
            occurred_at=message.created_at,
        )


async def save_results(
    uow: UnitOfWork,
    messages: list[OutboxMessage],
    results: list[BaseException | None],
) -> int:
    """Отметить успешные события published, упавшие - failed. Вернуть число успешных."""
    published_ids = []

    for message, result in zip(messages, results, strict=True):
        if isinstance(result, Exception):
            log.error(
                "Outbox event id=%s (%s) failed, attempt %d",
                message.id, message.routing_key, message.attempts + 1,
                exc_info=result,
            )
            await uow.outbox.mark_failed(message.id, repr(result))
        else:
            published_ids.append(message.id)

    await uow.outbox.mark_published(published_ids)
    return len(published_ids)


async def process_batch(
    batch_size: int,
    concurrency: int,
    *,
    bus: EventBus = event_bus,
    uow_factory: Callable[[], UnitOfWork] = UnitOfWork,
) -> int:
    """Обработать одну пачку событий и вернуть число взятых строк.

    События пачки обрабатываются параллельно, но не больше concurrency одновременно:
    каждый обработчик берёт соединение из пула БД. Строки заблокированы до конца
    транзакции (SKIP LOCKED). Успешные отмечаются published, упавшие получают +1 к
    attempts и остаются на следующую попытку.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async with uow_factory() as uow:
        messages = await uow.outbox.fetch_unpublished_for_update(batch_size)
        results = await asyncio.gather(
            *(dispatch(message, semaphore, bus) for message in messages),
            return_exceptions=True,
        )
        published = await save_results(uow, messages, results)

    if messages:
        log.info(
            "Outbox batch processed: %d published, %d failed",
            published, len(messages) - published,
        )
    return len(messages)
