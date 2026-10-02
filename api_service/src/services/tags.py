from src.core.logger import log
from src.core.uow import UnitOfWork
from src.models.tags import Tag


class TagService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def list_tags(self) -> list[Tag]:
        tags = await self.uow.tags.list_ordered_by_name()

        log.debug("Listed %d tags", len(tags))
        return tags
