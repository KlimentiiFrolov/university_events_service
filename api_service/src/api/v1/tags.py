from fastapi import APIRouter

from dependencies import TagServiceDep
from src.schemas.tags import TagListResponse, TagResponse

router = APIRouter(
    prefix="/tags",
    tags=["tags"],
)


@router.get("", response_model=TagListResponse)
async def list_tags(
    service: TagServiceDep,
) -> TagListResponse:
    tags = await service.list_tags()

    # Пагинации нет: список тегов отдаётся целиком, поэтому total равен числу items
    return TagListResponse(
        total=len(tags),
        # TODO: убрать после переноса преобразования сущностей в схемы в слой сервисов
        items=[TagResponse(id=tag.id, name=tag.name) for tag in tags],
    )
