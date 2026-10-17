from fastapi import APIRouter

from dependencies import TagServiceDep
from src.schemas.tags import TagListResponse

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
        items=tags,
    )
