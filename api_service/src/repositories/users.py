from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.users import User

from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            model=User,
            session=session,
        )

    async def get_by_email(
        self,
        email: str,
    ) -> User | None:
        return await self.session.scalar(
            select(User).where(User.email == email)
        )