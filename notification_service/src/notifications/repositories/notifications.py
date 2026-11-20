from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from notifications.models import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_many(self, notifications: list[Notification]) -> list[Notification]:
        self.session.add_all(notifications)
        await self.session.flush()

        return notifications

    async def list_undelivered(self, user_id: int) -> list[Notification]:
        result = await self.session.scalars(
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.delivered_at.is_(None),
            )
            .order_by(Notification.created_at, Notification.id)
        )
        return list(result.all())

    async def mark_delivered(self, notification_ids: list[int]) -> None:
        """Отметить отправленные клиенту уведомления, чтобы не досылать их снова."""
        if not notification_ids:
            return

        await self.session.execute(
            update(Notification)
            .where(
                Notification.id.in_(notification_ids),
                Notification.delivered_at.is_(None),
            )
            .values(delivered_at=func.now())
        )
