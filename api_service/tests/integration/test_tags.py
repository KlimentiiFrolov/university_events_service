from httpx import AsyncClient

from src.models.tags import Tag

TAGS_URL = "/api/v1/tags"


async def test_list_tags_returns_tags_sorted_by_name(
    api_client: AsyncClient,
    seed_tags: list[Tag],
) -> None:
    expected = sorted(seed_tags, key=lambda tag: tag.name)

    response = await api_client.get(TAGS_URL)

    assert response.status_code == 200
    assert response.json() == {
        "total": len(seed_tags),
        "items": [{"id": tag.id, "name": tag.name} for tag in expected],
    }


async def test_list_tags_returns_empty_list(api_client: AsyncClient) -> None:
    response = await api_client.get(TAGS_URL)

    assert response.status_code == 200
    assert response.json() == {"total": 0, "items": []}


async def test_list_tags_is_public(
    api_client: AsyncClient,
    seed_tags: list[Tag],
) -> None:
    # Справочник тегов нужен для фильтров каталога, поэтому доступен без авторизации
    response = await api_client.get(TAGS_URL, headers={})

    assert response.status_code == 200
    assert response.json()["total"] == len(seed_tags)
