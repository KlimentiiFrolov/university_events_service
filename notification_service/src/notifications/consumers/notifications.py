"""Consumer очереди уведомлений: сообщения api_service из RabbitMQ -> process_message."""

from collections.abc import Callable

import aio_pika
from aio_pika.abc import (
    AbstractChannel,
    AbstractConnection,
    AbstractIncomingMessage,
    AbstractQueue,
)
from sqlalchemy.ext.asyncio import AsyncSession

from notifications.core.config import RabbitMQSettings
from notifications.core.database import async_session_maker
from notifications.core.logger import log
from notifications.services.message_processor import ProcessStatus, process_message
from notifications.websocket.delivery import push_notifications
from notifications.websocket.manager import ConnectionManager


async def declare_topology(channel: AbstractChannel, config: RabbitMQSettings) -> AbstractQueue:
    """Объявить exchange, очередь уведомлений и DLQ для невалидных сообщений.

    Объявление идемпотентно: те же параметры можно объявлять при каждом старте.
    """
    exchange = await channel.declare_exchange(
        config.exchange,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )

    dead_letter_exchange = await channel.declare_exchange(
        config.dead_letter_exchange,
        aio_pika.ExchangeType.FANOUT,
        durable=True,
    )
    dead_letter_queue = await channel.declare_queue(config.dead_letter_queue, durable=True)
    await dead_letter_queue.bind(dead_letter_exchange)

    queue = await channel.declare_queue(
        config.queue,
        durable=True,
        arguments={"x-dead-letter-exchange": dead_letter_exchange.name},
    )
    for routing_key in config.routing_keys:
        await queue.bind(exchange, routing_key=routing_key)

    return queue


async def handle_message(
    message: AbstractIncomingMessage,
    *,
    session_factory: Callable[[], AsyncSession] = async_session_maker,
    manager: ConnectionManager | None = None,
) -> None:
    """Обработать сообщение, ответить брокеру и отправить уведомления тем, кто в сети.

    ack - после коммита, поэтому при падении сервиса сообщение придёт снова,
    а inbox отсечёт повтор. Невалидное - reject без возврата: уходит в DLQ.
    Ошибка обработки (например, БД недоступна) - nack с возвратом в очередь.
    """
    try:
        result = await process_message(message.body, session_factory=session_factory)
    except Exception:  # noqa: BLE001 - сообщение не должно потеряться из-за сбоя
        log.exception("Message id=%s processing failed, requeued", message.message_id)
        await message.nack(requeue=True)
        return

    if result.status == ProcessStatus.INVALID:
        await message.reject(requeue=False)
        return

    await message.ack()

    if manager is None or not result.notifications:
        return

    # Сообщение уже сохранено и подтверждено: сбой отправки не должен его затронуть,
    # недоставленные уведомления придут при следующем подключении
    try:
        await push_notifications(manager, result.notifications, session_factory)
    except Exception:  # noqa: BLE001
        log.exception("Pushing notifications of message id=%s failed", message.message_id)


async def start_consumer(
    connection: AbstractConnection,
    config: RabbitMQSettings,
    *,
    session_factory: Callable[[], AsyncSession] = async_session_maker,
    manager: ConnectionManager | None = None,
) -> AbstractChannel:
    """Подписаться на очередь уведомлений. Возвращает канал, закрытие которого
    останавливает consumer."""
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=config.prefetch_count)

    queue = await declare_topology(channel, config)

    async def on_message(message: AbstractIncomingMessage) -> None:
        await handle_message(message, session_factory=session_factory, manager=manager)

    await queue.consume(on_message)
    log.info("Consuming queue %s from exchange %s", config.queue, config.exchange)

    return channel
