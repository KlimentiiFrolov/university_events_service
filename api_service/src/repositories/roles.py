from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.roles import Role, RoleName

from .base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            model=Role,
            session=session,
        )

    async def get_by_name(
        self,
        name: RoleName,
    ) -> Role | None:
        return await self.session.scalar(
            select(Role).where(Role.name == name)
        )
