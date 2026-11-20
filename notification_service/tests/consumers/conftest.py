import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from uuid import uuid4

import aio_pika
import pytest
from aio_pika.abc import AbstractChannel, AbstractConnection
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from src.notifications.consumers.notifications import start_consumer
from src.notifications.core.config import RabbitMQSettings

RABBITMQ_USER = "test"
RABBITMQ_PASSWORD = "test"

type Publish = Callable[..., Awaitable[None]]


@pytest.fixture(scope="session")
def rabbitmq_container() -> Generator[DockerContainer, None, None]:
    container = (
        DockerContainer("rabbitmq:3-alpine")
        .with_env("RABBITMQ_DEFAULT_USER", RABBITMQ_USER)
        .with_env("RABBITMQ_DEFAULT_PASS", RABBITMQ_PASSWORD)
        .with_exposed_ports(5672)
    )
    with container:
        wait_for_logs(container, "Server startup complete", timeout=120)
        yield container


@pytest.fixture
def rabbitmq_settings(rabbitmq_container: DockerContainer) -> RabbitMQSettings:
    # Своя очередь на каждый тест: сообщения одного теста не достаются другому
    return RabbitMQSettings.model_construct(
        rabbit_protocol="amqp",
        rabbit_host=rabbitmq_container.get_container_host_ip(),
        rabbit_port=int(rabbitmq_container.get_exposed_port(5672)),
        rabbit_user=RABBITMQ_USER,
        rabbit_password=RABBITMQ_PASSWORD,
        exchange="test.events",
        queue=f"notifications-{uuid4().hex[:8]}",
    )


@pytest.fixture
async def rabbit_connection(
    rabbitmq_settings: RabbitMQSettings,
) -> AsyncGenerator[AbstractConnection, None]:
    connection = await aio_pika.connect(rabbitmq_settings.rabbitmq_url)
    yield connection
    await connection.close()


@pytest.fixture
async def consumer(
    rabbit_connection: AbstractConnection,
    rabbitmq_settings: RabbitMQSettings,
    session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AbstractChannel, None]:
    channel = await start_consumer(
        rabbit_connection,
        rabbitmq_settings,
        session_factory=session_maker,
    )
    yield channel
    if not channel.is_closed:
        await channel.close()


@pytest.fixture
async def publish(
    rabbit_connection: AbstractConnection,
    rabbitmq_settings: RabbitMQSettings,
) -> AsyncGenerator[Publish, None]:
    """Отправить сообщение в exchange так же, как это делает api_service."""
    channel = await rabbit_connection.channel()
    exchange = await channel.declare_exchange(
        rabbitmq_settings.exchange,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )

    async def _publish(body: bytes, routing_key: str = "registration.created") -> None:
        await exchange.publish(aio_pika.Message(body=body), routing_key=routing_key)

    yield _publish
    await channel.close()


async def wait_until(condition: Callable[[], Awaitable[bool]], timeout: float = 5.0) -> None:
    async def _poll() -> None:
        while not await condition():
            await asyncio.sleep(0.05)

    await asyncio.wait_for(_poll(), timeout)
