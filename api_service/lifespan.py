import asyncio

import grpc
from sqlalchemy import text

from src.clients.recommendations import RecommendationClient
from src.core.config import settings
from src.core.database import engine
from src.core.logger import log
from src.schemas.exceptions.database import DatabaseStartupException


class Lifespan:
    def __init__(self):
        self._recommendation_channel: grpc.aio.Channel | None = None
        self.recommendation_client: RecommendationClient | None = None

    async def startup(self):
        """Проверить подключение к внешним ресурсам при запуске приложения"""
        self._open_recommendation_channel()

        await asyncio.gather(
            self._check_database(),
        )

    async def shutdown(self):
        """Закрыть соединения при завершении приложения"""
        results = await asyncio.gather(
            self._engine_dispose(),
            self._close_recommendation_channel(),
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
