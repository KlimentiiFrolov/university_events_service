from datetime import datetime

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from src.core.dates import get_current_datetime
from src.models.event_tags import EventTag
from src.models.events import Event
from src.models.registrations import Registration, RegistrationStatus

from .base import BaseRepository


class EventRepository(BaseRepository[Event]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            model=Event,
            session=session,
        )

    @staticmethod
    def _with_tags(stmt: Select[tuple[Event]]) -> Select[tuple[Event]]:
        return stmt.options(
            selectinload(Event.event_tags).selectinload(EventTag.tag)
        )

    async def get_by_id(
        self,
        entity_id: int,
        *,
        with_tags: bool = False,
        for_update: bool = False,
    ) -> Event | None:
        stmt = select(Event).where(
            Event.id == entity_id,
            Event.deleted_at.is_(None),
        )

        if with_tags:
            stmt = self._with_tags(stmt)
        if for_update:
            stmt = stmt.with_for_update()

        return await self.session.scalar(stmt)

    async def list_filtered(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        tag_ids: list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Event]:
        stmt = self._with_tags(
            select(Event).where(Event.deleted_at.is_(None))
        )

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

        stmt = stmt.order_by(Event.event_date, Event.id).limit(limit).offset(offset)

        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_by_organizer(
        self,
        created_by_id: int,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Event]:
        stmt = (
            self._with_tags(select(Event))
            .where(
                Event.created_by_id == created_by_id,
                Event.deleted_at.is_(None),
            )
            .order_by(Event.event_date, Event.id)
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_recommendation_candidates(
        self,
        user_id: int,
        *,
        after: datetime | None = None,
        include_deleted: bool = False,
        limit: int = 1000,
    ) -> list[tuple[int, list[int]]]:
        if after is None:
            after = get_current_datetime()

        active_counts = (
            select(
                Registration.event_id,
                func.count(Registration.id).label("active_count"),
            )
            .where(Registration.status == RegistrationStatus.ACTIVE)
            .group_by(Registration.event_id)
            .subquery()
        )

        # Регистрация (user_id, event_id) уникальна, поэтому join не размножает строки
        user_registration = aliased(Registration)

        tag_ids = func.array_agg(EventTag.tag_id).filter(EventTag.tag_id.is_not(None))

        stmt = (
            select(Event.id, tag_ids)
            .outerjoin(EventTag, EventTag.event_id == Event.id)
            .outerjoin(active_counts, active_counts.c.event_id == Event.id)
            .outerjoin(
                user_registration,
                and_(
                    user_registration.event_id == Event.id,
                    user_registration.user_id == user_id,
                    user_registration.status == RegistrationStatus.ACTIVE,
                ),
            )
            .where(
                Event.event_date > after,
                # Без активных регистраций строки в active_counts нет, поэтому NULL -> 0
                func.coalesce(active_counts.c.active_count, 0) < Event.capacity,
                # Пользователь ещё не записан на мероприятие
                user_registration.id.is_(None),
            )
            .group_by(Event.id)
            .order_by(Event.event_date, Event.id)
            .limit(limit)
        )

        if not include_deleted:
            stmt = stmt.where(Event.deleted_at.is_(None))

        result = await self.session.execute(stmt)
        # array_agg по пустому набору возвращает NULL, а не пустой массив
        return [
            (event_id, event_tag_ids or []) 
            for event_id, event_tag_ids in result.all()
        ]
