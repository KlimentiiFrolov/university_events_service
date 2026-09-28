from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import Base


class BaseRepository[ModelT: Base]:
    def __init__(
        self,
        model: type[ModelT],
        session: AsyncSession,
    ):
        self.model = model
        self.session = session

    async def get_by_id(self, entity_id: int) -> ModelT | None:
        return await self.session.get(
            self.model,
            entity_id,
        )

    async def get_all(self) -> list[ModelT]:
        result = await self.session.scalars(
            select(self.model)
        )

        return list(result.all())

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)

        return entity

    async def update(self, entity: ModelT) -> ModelT:
        await self.session.flush()
        await self.session.refresh(entity)

        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()