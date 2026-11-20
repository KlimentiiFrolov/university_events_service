from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from notifications.models import InboxMessage


class InboxRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_if_new(self, message_id: UUID) -> bool:
        """Запомнить сообщение. False - оно уже было принято раньше (повторная доставка).

        Параллельная вставка того же message_id ждёт коммита первой и тоже вернёт False.
        """
        result = await self.session.execute(
            insert(InboxMessage)
            .values(message_id=message_id)
            .on_conflict_do_nothing(index_elements=[InboxMessage.message_id])
            .returning(InboxMessage.message_id)
        )
        return result.scalar_one_or_none() is not None
