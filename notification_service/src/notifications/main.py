"""Отдельный процесс сервиса уведомлений (NOTIFICATIONS_MODE=standalone).

Запуск: python -m notifications.main
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from notifications.api import main_router
from notifications.core.config import settings
from notifications.lifespan import NotificationLifespan


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    notification_lifespan = NotificationLifespan(settings.rabbitmq)
    notification_lifespan.bind(app)

    await notification_lifespan.start()
    yield
    await notification_lifespan.stop()


app = FastAPI(title="Notification Service", lifespan=lifespan)
app.include_router(main_router)


if __name__ == "__main__":
    uvicorn.run(app, host=settings.runtime.host, port=settings.runtime.port)
