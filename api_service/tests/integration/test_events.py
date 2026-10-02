import pytest
from httpx import AsyncClient

from src.models.event_tags import EventTag
from src.models.events import Event
from src.models.tags import Tag

EVENTS_URL = "/api/v1/events"


def _titles(response_json: dict) -> list[str]:
    return [event["title"] for event in response_json["items"]]


def _tag_names(event_json: dict) -> set[str]:
    return {tag["name"] for tag in event_json["tags"]}


# GET /events

async def test_list_events_returns_events_ordered_by_date(
    api_client: AsyncClient,
    seed_events: list[Event],
) -> None:
    response = await api_client.get(EVENTS_URL)

    assert response.status_code == 200
    assert _titles(response.json()) == ["Lecture", "Hackathon", "Workshop"]


async def test_list_events_returns_tags(
    api_client: AsyncClient,
    seed_event_tags: list[EventTag],
) -> None:
    response = await api_client.get(EVENTS_URL)

    assert response.status_code == 200
    lecture, hackathon, workshop = response.json()["items"]
    assert _tag_names(lecture) == {"IT"}
    assert _tag_names(hackathon) == {"IT", "Career"}
    assert _tag_names(workshop) == {"Sport"}


async def test_list_events_returns_empty_list(api_client: AsyncClient) -> None:
    response = await api_client.get(EVENTS_URL)

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 5, "page": 1}


async def test_list_events_filters_by_tag_ids(
    api_client: AsyncClient,
    seed_tags: list[Tag],
    seed_event_tags: list[EventTag],
) -> None:
    _, career, sport = seed_tags

    response = await api_client.get(
        EVENTS_URL,
        params={"tag_ids": [career.id, sport.id]},
    )

    assert response.status_code == 200
    assert _titles(response.json()) == ["Hackathon", "Workshop"]


async def test_list_events_filters_by_date_range(
    api_client: AsyncClient,
    seed_events: list[Event],
) -> None:
    response = await api_client.get(
        EVENTS_URL,
        params={
            "date_from": "2026-02-01T00:00:00Z",
            "date_to": "2026-02-28T23:59:59Z",
        },
    )

    assert response.status_code == 200
    assert _titles(response.json()) == ["Hackathon"]


async def test_list_events_hides_deleted_events(
    api_client: AsyncClient,
    event_service,
    seed_events: list[Event],
) -> None:
    lecture = seed_events[0]
    await event_service.delete_event(lecture.id, lecture.created_by_id)

    response = await api_client.get(EVENTS_URL)

    assert response.status_code == 200
    assert _titles(response.json()) == ["Hackathon", "Workshop"]


@pytest.mark.parametrize(
    "page,limit,expected_titles",
    [
        pytest.param(1, 1, ["Lecture"], id="first-page"),
        pytest.param(2, 1, ["Hackathon"], id="second-page"),
        pytest.param(2, 2, ["Workshop"], id="last-incomplete-page"),
        pytest.param(2, 20, [], id="past-the-end"),
    ],
)
async def test_list_events_paginates(
    api_client: AsyncClient,
    seed_events: list[Event],
    page: int,
    limit: int,
    expected_titles: list[str],
) -> None:
    response = await api_client.get(
        EVENTS_URL,
        params={"page": page, "limit": limit},
    )

    assert response.status_code == 200
    body = response.json()
    assert _titles(body) == expected_titles
    assert body["page"] == page


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"limit": 0}, id="limit-zero"),
        pytest.param({"limit": 101}, id="limit-too-big"),
        pytest.param({"page": 0}, id="page-zero"),
        pytest.param({"tag_ids": "abc"}, id="non-int-tag"),
        pytest.param({"date_from": "not-a-date"}, id="invalid-date"),
        pytest.param(
            {"date_from": "2026-03-01T00:00:00Z", "date_to": "2026-02-01T00:00:00Z"},
            id="inverted-date-range",
        ),
    ],
)
async def test_list_events_rejects_invalid_query(
    api_client: AsyncClient,
    params: dict,
) -> None:
    response = await api_client.get(EVENTS_URL, params=params)

    assert response.status_code == 422


# GET /events/{event_id}


async def test_get_event_returns_event_with_tags(
    api_client: AsyncClient,
    seed_events: list[Event],
    seed_event_tags: list[EventTag],
) -> None:
    hackathon = seed_events[1]

    response = await api_client.get(f"{EVENTS_URL}/{hackathon.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == hackathon.id
    assert body["title"] == "Hackathon"
    assert body["location"] == "Main Hall"
    assert body["capacity"] == 100
    assert body["created_by_id"] == hackathon.created_by_id
    assert _tag_names(body) == {"IT", "Career"}


async def test_get_event_without_tags_returns_empty_list(
    api_client: AsyncClient,
    seed_events: list[Event],
) -> None:
    response = await api_client.get(f"{EVENTS_URL}/{seed_events[0].id}")

    assert response.status_code == 200
    assert response.json()["tags"] == []


async def test_get_event_not_found(api_client: AsyncClient) -> None:
    response = await api_client.get(f"{EVENTS_URL}/999999")

    assert response.status_code == 404


async def test_get_event_deleted_returns_not_found(
    api_client: AsyncClient,
    event_service,
    seed_events: list[Event],
) -> None:
    lecture = seed_events[0]
    await event_service.delete_event(lecture.id, lecture.created_by_id)

    response = await api_client.get(f"{EVENTS_URL}/{lecture.id}")

    assert response.status_code == 404


async def test_get_event_rejects_non_int_id(api_client: AsyncClient) -> None:
    response = await api_client.get(f"{EVENTS_URL}/abc")

    assert response.status_code == 422
