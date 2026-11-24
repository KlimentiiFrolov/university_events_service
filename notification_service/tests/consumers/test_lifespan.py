import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import aio_pika
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from notifications.api import main_router
from notifications.core.config import RabbitMQSettings
from notifications.lifespan import NotificationLifespan

from ..tokens import bearer, make_token
from ..websocket.test_manager import FakeWebSocket
from .conftest import Publish, wait_until
from .test_notifications_consumer import body

USER_ID = 7


async def test_lifespan_consumes_and_pushes_to_its_manager(
    publish: Publish,
    rabbitmq_settings: RabbitMQSettings,
    session_maker: async_sessionmaker[AsyncSession],
):
    notification_lifespan = NotificationLifespan(rabbitmq_settings, session_factory=session_maker)
    websocket = FakeWebSocket()
    notification_lifespan.manager.connect(USER_ID, websocket)
    await notification_lifespan.start()

    await publish(body())

    async def pushed() -> bool:
        return len(websocket.sent) == 1

    await wait_until(pushed)
    await notification_lifespan.stop()


async def test_stop_without_start_does_nothing(rabbitmq_settings: RabbitMQSettings):
    await NotificationLifespan(rabbitmq_settings).stop()


def test_message_from_broker_reaches_websocket_client(
    rabbitmq_settings: RabbitMQSettings,
    db_url: str,
    clean_db: None,
):
    """Сквозной путь: RabbitMQ -> consumer -> БД -> WebSocket-клиент."""
    # NullPool: приложение работает в потоке TestClient со своим event loop
    session_factory = async_sessionmaker(
        create_async_engine(db_url, poolclass=NullPool),
        expire_on_commit=False,
    )
    notification_lifespan = NotificationLifespan(rabbitmq_settings, session_factory=session_factory)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        await notification_lifespan.start()
        yield
        await notification_lifespan.stop()

    app = FastAPI(lifespan=lifespan)
    app.include_router(main_router)
    notification_lifespan.bind(app)

    async def publish_to_broker() -> None:
        connection = await aio_pika.connect(rabbitmq_settings.rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            exchange = await channel.get_exchange(rabbitmq_settings.exchange)
            await exchange.publish(aio_pika.Message(body=body()), routing_key="registration.created")

    with TestClient(app) as client:
        response = client.post("/ws/tickets", headers=bearer(make_token(USER_ID)))
        ticket = response.json()["ticket"]

        with client.websocket_connect("/ws/notifications", headers=bearer(ticket)) as websocket:
            asyncio.run(publish_to_broker())
            # Даже если сообщение обработается раньше регистрации подключения,
            # уведомление придёт досылкой недоставленного
            message = websocket.receive_json()

    assert message["type"] == "notification"
    assert message["title"] == "Новая запись на мероприятие"
