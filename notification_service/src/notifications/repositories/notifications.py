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

    async def mark_delivered(self, notification_id: int, user_id: int) -> bool:
        """Отметить доставленным. False - чужое, несуществующее или уже доставленное."""
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.delivered_at.is_(None),
            )
            .values(delivered_at=func.now())
            .returning(Notification.id)
        )
        return result.scalar_one_or_none() is not None
