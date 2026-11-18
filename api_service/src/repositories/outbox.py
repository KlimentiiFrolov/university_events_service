from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dates import get_current_datetime
from src.events.types import DomainEventType
from src.models.outbox import OutboxMessage

from .base import BaseRepository


class OutboxRepository(BaseRepository[OutboxMessage]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            model=OutboxMessage,
            session=session,
        )

    async def add_event(self, event_type: DomainEventType, payload: BaseModel) -> OutboxMessage:
        """Записать доменное событие в outbox в текущей транзакции.

        id и created_at заполняются автоматически и дальше служат id и временем события.
        """
        return await self.add(
            OutboxMessage(
                routing_key=event_type,
                payload=payload.model_dump(mode="json"),
            )
        )

    async def fetch_unpublished_for_update(self, limit: int) -> list[OutboxMessage]:
        """Взять батч неотправленных сообщений и заблокировать их до конца транзакции.

        "SKIP LOCKED": строки, уже взятые другим relay, пропускаются, а не ожидаются.
        """
        result = await self.session.scalars(
            select(OutboxMessage)
            .where(OutboxMessage.published_at.is_(None))
            .order_by(OutboxMessage.created_at, OutboxMessage.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result.all())

    async def mark_published(self, message_ids: list[UUID]) -> None:
        if not message_ids:
            return

        await self.session.execute(
            update(OutboxMessage)
            .where(OutboxMessage.id.in_(message_ids))
            .values(published_at=get_current_datetime())
        )

    async def mark_failed(self, message_id: UUID, error: str) -> None:
        await self.session.execute(
            update(OutboxMessage)
            .where(OutboxMessage.id == message_id)
            .values(
                attempts=OutboxMessage.attempts + 1,
                last_error=error,
            )
        )
