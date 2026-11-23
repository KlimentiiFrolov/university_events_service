import asyncio

import grpc
from sqlalchemy import text

from src.clients.rabbitmq import rabbit_publisher
from src.clients.recommendations import RecommendationClient
from src.core.config import settings
from src.core.database import engine
from src.core.logger import log
from src.outbox.relay import run_relay
from src.schemas.exceptions.database import DatabaseStartupException

# Сколько ждать, пока relay доделает текущую пачку. С запасом до SIGKILL от docker stop (10 с)
RELAY_SHUTDOWN_TIMEOUT = 5.0


class Lifespan:
    def __init__(self):
        self._recommendation_channel: grpc.aio.Channel | None = None
        self.recommendation_client: RecommendationClient | None = None
        self._relay_stop = asyncio.Event()
        self._relay_task: asyncio.Task[None] | None = None

    async def startup(self):
        """Проверить подключение к внешним ресурсам при запуске приложения"""
        self._open_recommendation_channel()

        await asyncio.gather(
            self._check_database(),
        )

        await self._start_relay()

    async def shutdown(self):
        """Закрыть соединения при завершении приложения"""
        # Relay работает с БД и брокером, поэтому останавливается до их закрытия
        await self._stop_relay()

        results = await asyncio.gather(
            self._engine_dispose(),
            self._close_recommendation_channel(),
            rabbit_publisher.close(),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                log.error("Unexpected error during shutdown: %s", result)

    async def _check_database(self) -> None:
        """Проверить подключение к базе данных"""
        try:
            async with engine.connect() as connection:
                result = await connection.scalar(text("SELECT 1"))
        except Exception as e:
            log.error("Failed to connect database: %s", e)
            raise DatabaseStartupException(f"Unexpected error during connection to database: {e}") from e

        if result != 1:
            raise DatabaseStartupException(f"Database returned unexpected result: {result}")

        log.info("Database successful connected")

    async def _engine_dispose(self) -> None:
        await engine.dispose()
        log.info("Engine successful disposed!")

    def _open_recommendation_channel(self) -> None:
        target = settings.recommendation.grpc_target
        self._recommendation_channel = grpc.aio.insecure_channel(target)
        self.recommendation_client = RecommendationClient(
            self._recommendation_channel,
            timeout=settings.recommendation.timeout,
        )
        log.info("Recommendation gRPC channel opened to %s", target)

    async def _close_recommendation_channel(self) -> None:
        if self._recommendation_channel is None:
            return

        await self._recommendation_channel.close()
        log.info("Recommendation gRPC channel closed!")

    async def _start_relay(self) -> None:
        """Подключиться к RabbitMQ и запустить outbox relay фоновой задачей"""
        if not settings.outbox.relay_enabled:
            log.info("Outbox relay is disabled")
            return

        await rabbit_publisher.connect()
        self._relay_task = asyncio.create_task(run_relay(self._relay_stop, settings.outbox))

    async def _stop_relay(self) -> None:
        """Дать relay доделать текущую пачку; не успел за таймаут - отменить"""
        if self._relay_task is None:
            return

        self._relay_stop.set()
        try:
            # По таймауту wait_for сам отменяет задачу: транзакция пачки откатится,
            # строки останутся в outbox и уйдут после перезапуска
            await asyncio.wait_for(self._relay_task, timeout=RELAY_SHUTDOWN_TIMEOUT)
        except TimeoutError:
            log.warning("Outbox relay did not stop in %.0fs, cancelled", RELAY_SHUTDOWN_TIMEOUT)
