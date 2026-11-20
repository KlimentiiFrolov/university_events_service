"""Обработка одного сообщения из очереди: валидация, inbox, сохранение уведомлений."""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from notifications.core.database import async_session_maker
from notifications.core.logger import log
from notifications.models import Notification
from notifications.repositories.inbox import InboxRepository
from notifications.repositories.notifications import NotificationRepository
from notifications.schemas.messages import NotificationMessage
from notifications.services.notification_builder import build_notification


class ProcessStatus(StrEnum):
    PROCESSED = "processed"  # новое сообщение, уведомления сохранены
    DUPLICATE = "duplicate"  # уже обработано раньше, ничего не сделано
    INVALID = "invalid"  # не разбирается, повторять бессмысленно


@dataclass(frozen=True)
class ProcessResult:
    status: ProcessStatus
    notifications: list[Notification] = field(default_factory=list)


async def process_message(
    body: bytes,
    *,
    session_factory: Callable[[], AsyncSession] = async_session_maker,
) -> ProcessResult:
    """Разобрать сообщение и сохранить уведомления получателям.

    Запись в inbox и уведомления - одна транзакция: либо сообщение принято целиком,
    либо его можно безопасно обработать заново.
    """
    try:
        message = NotificationMessage.model_validate_json(body)
        content = build_notification(message)
    except ValidationError as error:
        log.error("Invalid message rejected: %s", error)
        return ProcessResult(ProcessStatus.INVALID)

    async with session_factory() as session, session.begin():
        if not await InboxRepository(session).add_if_new(message.message_id):
            log.warning("Message id=%s already processed, skipped", message.message_id)
            return ProcessResult(ProcessStatus.DUPLICATE)

        notifications = await NotificationRepository(session).add_many([
            Notification(
                message_id=message.message_id,
                user_id=user_id,
                type=message.type,
                title=content.title,
                text=content.text,
                data=message.data,
            )
            for user_id in message.recipient_ids
        ])

    log.info(
        "Message id=%s (%s) processed: %d notification(s) saved",
        message.message_id, message.type, len(notifications),
    )
    return ProcessResult(ProcessStatus.PROCESSED, notifications)
