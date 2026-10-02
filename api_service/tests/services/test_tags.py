from src.models.tags import Tag
from src.services.tags import TagService


async def test_list_tags_returns_all_tags_sorted_by_name(
    tag_service: TagService,
    seed_tags: list[Tag],
):
    tags = await tag_service.list_tags()

    assert [tag.name for tag in tags] == sorted(tag.name for tag in seed_tags)


async def test_list_tags_returns_empty_list_without_tags(tag_service: TagService):
    assert await tag_service.list_tags() == []
