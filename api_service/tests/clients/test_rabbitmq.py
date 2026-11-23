from uuid import uuid4

import aio_pika
import pytest
from aio_pika.exceptions import DeliveryError

from src.clients.rabbitmq import RabbitPublisher
from src.core.config import RabbitMQSettings


async def test_publish_delivers_persistent_json_message(
    rabbit_publisher: RabbitPublisher,
    receive_message,
):
    message_id = uuid4()

    await rabbit_publisher.publish(
        routing_key="registration.created",
        body=b'{"event_id": 1}',
        message_id=message_id,
    )

    message = await receive_message()
    assert message.body == b'{"event_id": 1}'
    assert message.routing_key == "registration.created"
    assert message.message_id == str(message_id)
    assert message.content_type == "application/json"
    assert message.delivery_mode == aio_pika.DeliveryMode.PERSISTENT


async def test_publish_without_connect_raises(rabbitmq_settings: RabbitMQSettings):
    publisher = RabbitPublisher(rabbitmq_settings)

    with pytest.raises(RuntimeError, match="not connected"):
        await publisher.publish(routing_key="event.updated", body=b"{}", message_id=uuid4())


async def test_close_without_connect_does_nothing(rabbitmq_settings: RabbitMQSettings):
    await RabbitPublisher(rabbitmq_settings).close()


async def test_publish_without_bound_queue_raises(rabbit_publisher: RabbitPublisher):
    # Очередь к exchange не привязана (фикстура rabbit_queue не используется)
    with pytest.raises(DeliveryError):
        await rabbit_publisher.publish(
            routing_key="registration.created",
            body=b"{}",
            message_id=uuid4(),
        )
