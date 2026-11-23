"""Обработчики доменных событий и их регистрация в шине.

Новое событие: написать функцию-обработчик с декоратором @event_bus.register(...).
Обработчики вызываются relay для событий из outbox; событие уже закоммичено,
поэтому каждый обработчик открывает свой UoW только для чтения.
"""

from uuid import uuid5

from pydantic import BaseModel

from src.clients.rabbitmq import rabbit_publisher
from src.core.logger import log
from src.core.uow import UnitOfWork
from src.schemas.messages import (
    EventNotificationData,
    NotificationMessage,
    RegistrationNotificationData,
)

from .bus import EventBus
from .payloads import (
    EventCancelledPayload,
    EventUpdatedPayload,
    RegistrationCancelledPayload,
    RegistrationCreatedPayload,
)
from .types import DomainEvent, DomainEventType

NOTIFICATIONS_CHANNEL = "notifications"

event_bus = EventBus()


async def send_message(
    event: DomainEvent,
    channel: str,
    recipient_ids: list[int],
    data: BaseModel,
) -> None:
    if not recipient_ids:
        log.debug("Domain event %s id=%s has no recipients, skipped", event.type, event.id)
        return

    message = NotificationMessage(
        # Стабилен при повторной обработке события и свой у каждого канала:
        # inbox потребителя отсекает дубли, но не путает сообщения разных каналов
        message_id=uuid5(event.id, channel),
        event_id=event.id,
        type=event.type,
        occurred_at=event.occurred_at,
        recipient_ids=recipient_ids,
        data=data.model_dump(mode="json"),
    )

    await rabbit_publisher.publish(
        routing_key=event.type,
        body=message.model_dump_json().encode(),
        message_id=message.message_id,
    )

    log.info(
        "Message id=%s (%s, channel=%s) sent for %d recipient(s)",
        message.message_id, event.type, channel, len(recipient_ids),
    )


async def notify_organizer(event: DomainEvent, event_id: int, user_id: int) -> None:
    async with UnitOfWork() as uow:
        target = await uow.events.get_by_id(event_id)
        participant = await uow.users.get_by_id(user_id)

    if target is None or participant is None:
        log.warning(
            "Event id=%d or user id=%d not found, %s id=%s skipped",
            event_id, user_id, event.type, event.id,
        )
        return

    await send_message(
        event,
        NOTIFICATIONS_CHANNEL,
        recipient_ids=[target.created_by_id],
        data=RegistrationNotificationData(
            event_id=target.id,
            event_title=target.title,
            participant_id=participant.id,
            participant_name=f"{participant.first_name} {participant.second_name}",
        ),
    )


@event_bus.register(DomainEventType.REGISTRATION_CREATED)
async def on_registration_created(event: DomainEvent) -> None:
    payload = RegistrationCreatedPayload.model_validate(event.payload)
    await notify_organizer(event, payload.event_id, payload.user_id)


@event_bus.register(DomainEventType.REGISTRATION_CANCELLED)
async def on_registration_cancelled(event: DomainEvent) -> None:
    payload = RegistrationCancelledPayload.model_validate(event.payload)
    await notify_organizer(event, payload.event_id, payload.user_id)


@event_bus.register(DomainEventType.EVENT_UPDATED)
async def on_event_updated(event: DomainEvent) -> None:
    payload = EventUpdatedPayload.model_validate(event.payload)

    async with UnitOfWork() as uow:
        target = await uow.events.get_by_id(payload.event_id)
        participants = await uow.registrations.get_event_participants(payload.event_id)

    if target is None:
        log.warning("Event id=%d not found, %s id=%s skipped", payload.event_id, event.type, event.id)
        return

    await send_message(
        event,
        NOTIFICATIONS_CHANNEL,
        recipient_ids=[participant.id for participant in participants],
        data=EventNotificationData(
            event_id=target.id,
            event_title=target.title,
            event_date=target.event_date,
            location=target.location,
            changed_fields=payload.changed_fields,
        ),
    )


@event_bus.register(DomainEventType.EVENT_CANCELLED)
async def on_event_cancelled(event: DomainEvent) -> None:
    payload = EventCancelledPayload.model_validate(event.payload)

    async with UnitOfWork() as uow:
        # Мероприятие уже мягко удалено, get_by_id его не вернёт
        events = await uow.events.list_by_ids([payload.event_id], include_deleted=True)

    if not events:
        log.warning("Event id=%d not found, %s id=%s skipped", payload.event_id, event.type, event.id)
        return

    target = events[0]
    await send_message(
        event,
        NOTIFICATIONS_CHANNEL,
        recipient_ids=payload.participant_ids,
        data=EventNotificationData(
            event_id=target.id,
            event_title=target.title,
            event_date=target.event_date,
            location=target.location,
        ),
    )
