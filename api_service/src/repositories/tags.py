from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.tags import Tag

from .base import BaseRepository


class TagRepository(BaseRepository[Tag]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            model=Tag,
            session=session,
        )

    async def get_by_name(self, name: str) -> Tag | None:
        return await self.session.scalar(
            select(Tag).where(Tag.name == name)
        )

    async def list_by_names(self, names: list[str]) -> list[Tag]:
        result = await self.session.scalars(
            select(Tag).where(Tag.name.in_(names))
        )
        return list(result.all())

    async def list_by_ids(self, ids: list[int]) -> list[Tag]:
        result = await self.session.scalars(
            select(Tag).where(Tag.id.in_(ids))
        )
        return list(result.all())
