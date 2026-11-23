from uuid import UUID

import aio_pika
from aio_pika.abc import AbstractExchange, AbstractRobustConnection

from src.core.config import RabbitMQSettings, settings
from src.core.logger import log


class RabbitPublisher:
    """Публикует сообщения в topic exchange с подтверждением от брокера."""

    def __init__(self, config: RabbitMQSettings):
        self._config = config
        self._connection: AbstractRobustConnection | None = None
        self._exchange: AbstractExchange | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._config.rabbitmq_url)
        # publisher_confirms=True: publish() ждёт подтверждения от брокера
        channel = await self._connection.channel(publisher_confirms=True)
        self._exchange = await channel.declare_exchange(
            self._config.exchange,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        log.info("RabbitMQ publisher connected, exchange=%s", self._config.exchange)

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            log.info("RabbitMQ publisher closed")

    async def publish(self, routing_key: str, body: bytes, message_id: UUID) -> None:
        if self._exchange is None:
            raise RuntimeError("RabbitPublisher is not connected")

        await self._exchange.publish(
            aio_pika.Message(
                body=body,
                message_id=str(message_id),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=routing_key,
        )


rabbit_publisher = RabbitPublisher(settings.rabbitmq)
