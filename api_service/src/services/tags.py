from src.core.logger import log
from src.core.uow import UnitOfWork
from src.schemas.tags import TagResponse


class TagService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def list_tags(self) -> list[TagResponse]:
        tags = await self.uow.tags.list_ordered_by_name()

        log.debug("Listed %d tags", len(tags))
        return [TagResponse.model_validate(tag) for tag in tags]
