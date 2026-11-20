"""Отдельный процесс сервиса уведомлений (NOTIFICATIONS_MODE=standalone).

Запуск: python -m notifications.main
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from notifications.core.config import settings
from notifications.lifespan import NotificationLifespan

notification_lifespan = NotificationLifespan(settings.rabbitmq)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await notification_lifespan.start()
    yield
    await notification_lifespan.stop()


app = FastAPI(title="Notification Service", lifespan=lifespan)
app.include_router(notification_lifespan.build_router(settings.auth))


if __name__ == "__main__":
    uvicorn.run(app, host=settings.runtime.host, port=settings.runtime.port)
