from src.models.tags import Tag
from src.schemas.tags import TagResponse
from src.services.tags import TagService


async def test_list_tags_returns_all_tags_sorted_by_name(
    tag_service: TagService,
    seed_tags: list[Tag],
):
    tags = await tag_service.list_tags()

    assert tags == [
        TagResponse(id=tag.id, name=tag.name)
        for tag in sorted(seed_tags, key=lambda tag: tag.name)
    ]


async def test_list_tags_returns_empty_list_without_tags(tag_service: TagService):
    assert await tag_service.list_tags() == []
