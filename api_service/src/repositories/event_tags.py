from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.event_tags import EventTag

from .base import BaseRepository


class EventTagRepository(BaseRepository[EventTag]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            model=EventTag,
            session=session,
        )

    async def get_by_event_and_tag(
        self,
        event_id: int,
        tag_id: int,
    ) -> EventTag | None:
        return await self.session.get(EventTag, (event_id, tag_id))

    async def list_by_event(self, event_id: int) -> list[EventTag]:
        result = await self.session.scalars(
            select(EventTag).where(EventTag.event_id == event_id)
        )
        return list(result.all())

    async def list_by_tag(self, tag_id: int) -> list[EventTag]:
        result = await self.session.scalars(
            select(EventTag).where(EventTag.tag_id == tag_id)
        )
        return list(result.all())

    async def add_tags(
        self,
        event_id: int,
        tag_ids: list[int],
    ) -> list[EventTag]:
        event_tags = [
            EventTag(event_id=event_id, tag_id=tag_id)
            for tag_id in tag_ids
        ]

        try:
            self.session.add_all(event_tags)
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise

        return event_tags

    async def replace_tags(
        self,
        event_id: int,
        tag_ids: list[int],
    ) -> list[EventTag]:
        await self.delete_by_event(event_id)
        return await self.add_tags(event_id, tag_ids)

    async def delete_by_event(self, event_id: int) -> None:
        await self.session.execute(
            delete(EventTag).where(EventTag.event_id == event_id)
        )
        await self.session.commit()
