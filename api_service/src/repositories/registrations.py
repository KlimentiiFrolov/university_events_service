from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.events import Event
from src.models.registrations import Registration
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

    async def get_user(
        self,
        user_id: int,
    ) -> User | None:
        return await self.session.get(
            User,
            user_id,
        )

    async def get_event(
        self,
        event_id: int,
    ) -> Event | None:
        return await self.session.get(
            Event,
            event_id,
        )

    async def count_active_for_event(
        self,
        event_id: int,
    ) -> int:
        count = await self.session.scalar(
            select(func.count(Registration.id)).where(
                Registration.event_id == event_id,
                Registration.status == "active",
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
                Registration.status == "active",
            )
        )

        return list(result.all())