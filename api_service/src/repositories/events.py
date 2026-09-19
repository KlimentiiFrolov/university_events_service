from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.event_tags import EventTag
from src.models.events import Event

from .base import BaseRepository


class EventRepository(BaseRepository[Event]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            model=Event,
            session=session,
        )

    async def get_by_id(
        self,
        entity_id: int,
        *,
        with_tags: bool = False,
        for_update: bool = False,
    ) -> Event | None:
        stmt = select(Event).where(Event.id == entity_id)

        if with_tags:
            stmt = stmt.options(
                selectinload(Event.event_tags).selectinload(EventTag.tag)
            )
        if for_update:
            stmt = stmt.with_for_update()

        return await self.session.scalar(stmt)

    async def list_filtered(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        tag_ids: list[int] | None = None,
    ) -> list[Event]:
        stmt = select(Event)

        if date_from is not None:
            stmt = stmt.where(Event.event_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Event.event_date <= date_to)
        if tag_ids:
            stmt = (
                stmt.join(Event.event_tags)
                .where(EventTag.tag_id.in_(tag_ids))
                .distinct()
            )

        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_by_organizer(self, created_by_id: int) -> list[Event]:
        result = await self.session.scalars(
            select(Event).where(Event.created_by_id == created_by_id)
        )
        return list(result.all())
