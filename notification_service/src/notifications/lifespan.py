"""Жизненный цикл сервиса уведомлений: consumer RabbitMQ + реестр WebSocket-подключений.

Подключается из lifespan: своего приложения (standalone) или api_service (embedded).
"""

from collections.abc import Callable

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractRobustConnection
from fastapi import APIRouter, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from notifications.consumers.notifications import start_consumer
from notifications.core.config import AuthSettings, RabbitMQSettings
from notifications.core.database import async_session_maker, engine
from notifications.core.logger import log
from notifications.websocket.endpoint import build_router
from notifications.websocket.manager import ConnectionManager
from notifications.websocket.tickets import TicketStore


class NotificationLifespan:
    def __init__(
        self,
        rabbitmq: RabbitMQSettings,
        *,
        session_factory: Callable[[], AsyncSession] = async_session_maker,
    ) -> None:
        self._rabbitmq = rabbitmq
        self.session_factory = session_factory
        # Один реестр на процесс: в него пишет WS-эндпоинт, из него читает consumer
        self.manager = ConnectionManager()
        # Тикеты выдаёт и гасит этот же процесс
        self.tickets = TicketStore()
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractChannel | None = None

    def bind(self, app: FastAPI) -> None:
        """Сделать состояние доступным зависимостям (notifications.dependencies) через app.state.

        Один ключ, а не по ключу на объект: в режиме embedded app.state общий с api_service.
        """
        app.state.notifications = self

    def build_router(self, auth: AuthSettings) -> APIRouter:
        return build_router(self.manager, auth, session_factory=self.session_factory)

    async def start(self) -> None:
        self._connection = await aio_pika.connect_robust(self._rabbitmq.rabbitmq_url)
        self._channel = await start_consumer(
            self._connection,
            self._rabbitmq,
            session_factory=self.session_factory,
            manager=self.manager,
        )
        log.info("Notification lifespan started")

    async def stop(self) -> None:
        if self._channel is not None:
            await self._channel.close()
        if self._connection is not None:
            await self._connection.close()
        await engine.dispose()
        log.info("Notification lifespan stopped")
