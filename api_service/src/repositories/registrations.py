from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dates import get_current_datetime
from src.models.event_tags import EventTag
from src.models.events import Event
from src.models.registrations import (
    Registration,
    RegistrationStatus,
)
from src.models.users import User

from .base import BaseRepository


class RegistrationRepository(BaseRepository[Registration]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            model=Registration,
            session=session,
        )

    async def get_by_user_and_event(
        self,
        user_id: int,
        event_id: int,
    ) -> Registration | None:
        return await self.session.scalar(
            select(Registration).where(
                Registration.user_id == user_id,
                Registration.event_id == event_id,
            )
        )

    async def get_by_user_id(
        self,
        user_id: int,
    ) -> list[Registration]:
        result = await self.session.scalars(
            select(Registration).where(
                Registration.user_id == user_id
            )
        )

        return list(result.all())

    async def list_visited_tag_ids(
        self,
        user_id: int,
        *,
        status: RegistrationStatus = RegistrationStatus.ACTIVE,
        before: datetime | None = None,
    ) -> list[int]:
        if before is None:
            before = get_current_datetime()

        result = await self.session.scalars(
            select(EventTag.tag_id)
            .join(Registration, Registration.event_id == EventTag.event_id)
            .join(Event, Event.id == EventTag.event_id)
            .where(
                Registration.user_id == user_id,
                Registration.status == status,
                Event.event_date < before,
            )
            .distinct()
        )

        return list(result.all())

    async def count_active_for_event(
        self,
        event_id: int,
    ) -> int:
        count = await self.session.scalar(
            select(func.count(Registration.id)).where(
                Registration.event_id == event_id,
                Registration.status == RegistrationStatus.ACTIVE,
            )
        )

        return count or 0

    async def get_event_participants(
        self,
        event_id: int,
    ) -> list[User]:
        result = await self.session.scalars(
            select(User)
            .join(
                Registration,
                Registration.user_id == User.id,
            )
            .where(
                Registration.event_id == event_id,
                Registration.status == RegistrationStatus.ACTIVE,
            )
        )

        return list(result.all())

    async def cancel_all_active_for_event(self, event_id: int) -> None:
        await self.session.execute(
            update(Registration)
            .where(
                Registration.event_id == event_id,
                Registration.status == RegistrationStatus.ACTIVE,
            )
            .values(
                status=RegistrationStatus.CANCELLED,
                cancelled_at=get_current_datetime(),
            )
        )
        await self.session.flush()