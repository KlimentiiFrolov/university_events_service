import asyncio

from sqlalchemy import text

from src.core.database import engine
from src.core.logger import log
from src.schemas.exceptions.database import DatabaseStartupException


class Lifespan:
    async def startup(self):
        """Проверить подключение к внешним ресурсам при запуске приложения"""
        await asyncio.gather(
            self._check_database(),
        )

    async def shutdown(self):
        """Закрыть соединения при завершении приложения"""
        results = await asyncio.gather(
            self._engine_dispose(),
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
