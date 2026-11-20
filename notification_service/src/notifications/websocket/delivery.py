"""Отправка новых уведомлений пользователям, которые сейчас в сети."""

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from notifications.core.logger import log
from notifications.models import Notification
from notifications.repositories.notifications import NotificationRepository
from notifications.schemas.websocket import NotificationPayload

from .manager import ConnectionManager


async def push_notifications(
    manager: ConnectionManager,
    notifications: list[Notification],
    session_factory: Callable[[], AsyncSession],
) -> None:
    """Отправить уведомления их получателям и отметить доставленными отправленные.

    Пользователь не в сети - уведомление остаётся недоставленным и придёт при подключении.
    """
    delivered_ids = []
    for notification in notifications:
        payload = NotificationPayload.from_model(notification).model_dump(mode="json")
        if await manager.send_to_user(notification.user_id, payload):
            delivered_ids.append(notification.id)

    if not delivered_ids:
        return

    async with session_factory() as session, session.begin():
        await NotificationRepository(session).mark_delivered(delivered_ids)

    log.info("Pushed %d of %d notification(s) to online users", len(delivered_ids), len(notifications))


async def push_undelivered(
    manager: ConnectionManager,
    user_id: int,
    session_factory: Callable[[], AsyncSession],
) -> None:
    """Дослать пользователю уведомления, которые он ещё не получил (например, был не в сети)."""
    async with session_factory() as session:
        undelivered = await NotificationRepository(session).list_undelivered(user_id)

    await push_notifications(manager, undelivered, session_factory)
