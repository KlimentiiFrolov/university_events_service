import pytest
from httpx import AsyncClient

from src.models.event_tags import EventTag
from src.models.events import Event
from src.models.roles import RoleName
from src.models.tags import Tag
from src.models.users import User

EVENTS_URL = "/api/v1/events"


def _titles(response_json: dict) -> list[str]:
    return [event["title"] for event in response_json["items"]]


def _tag_names(event_json: dict) -> set[str]:
    return {tag["name"] for tag in event_json["tags"]}


# TODO: заменить на Authorization: Bearer после появления зависимости авторизации по JWT
def _auth_headers(user: User) -> dict[str, str]:
    return {"X-User-Id": str(user.id)}


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
    assert body["title"] == hackathon.title
    assert body["location"] == hackathon.location
    assert body["capacity"] == hackathon.capacity
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


# POST /events

EVENT_BODY = {
    "title": "Meetup",
    "text": "Evening meetup",
    "location": "Room 303",
    "event_date": "2026-04-01T18:00:00Z",
    "capacity": 50,
}


async def test_create_event_returns_created_event(
    api_client: AsyncClient,
    make_user,
) -> None:
    organizer = await make_user(role=RoleName.ORGANIZER)

    response = await api_client.post(
        EVENTS_URL,
        headers=_auth_headers(organizer),
        json=EVENT_BODY,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["title"] == EVENT_BODY["title"]
    assert body["text"] == EVENT_BODY["text"]
    assert body["location"] == EVENT_BODY["location"]
    assert body["event_date"] == EVENT_BODY["event_date"]
    assert body["capacity"] == EVENT_BODY["capacity"]
    assert body["created_by_id"] == organizer.id
    assert body["created_at"]
    assert body["tags"] == []


async def test_create_event_is_available_afterwards(
    api_client: AsyncClient,
    make_user,
) -> None:
    organizer = await make_user(role=RoleName.ORGANIZER)

    created = await api_client.post(
        EVENTS_URL,
        headers=_auth_headers(organizer),
        json=EVENT_BODY,
    )

    fetched = await api_client.get(f"{EVENTS_URL}/{created.json()['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == created.json()

    listed = await api_client.get(EVENTS_URL)
    assert _titles(listed.json()) == ["Meetup"]


async def test_create_event_with_tags(
    api_client: AsyncClient,
    make_user,
    seed_tags: list[Tag],
) -> None:
    organizer = await make_user(role=RoleName.ORGANIZER)
    it, career, _ = seed_tags

    response = await api_client.post(
        EVENTS_URL,
        headers=_auth_headers(organizer),
        json={**EVENT_BODY, "tag_ids": [it.id, career.id, it.id]},
    )

    assert response.status_code == 201
    assert _tag_names(response.json()) == {"IT", "Career"}


async def test_create_event_requires_auth(api_client: AsyncClient) -> None:
    response = await api_client.post(EVENTS_URL, json=EVENT_BODY)

    assert response.status_code == 401


async def test_create_event_with_unknown_user(
    api_client: AsyncClient,
) -> None:
    response = await api_client.post(
        EVENTS_URL,
        headers={"X-User-Id": "999999"},
        json=EVENT_BODY,
    )

    assert response.status_code == 404


async def test_create_event_with_unknown_tag(
    api_client: AsyncClient,
    make_user,
    seed_tags: list[Tag],
) -> None:
    organizer = await make_user(role=RoleName.ORGANIZER)
    it, _, _ = seed_tags

    response = await api_client.post(
        EVENTS_URL,
        headers=_auth_headers(organizer),
        json={**EVENT_BODY, "tag_ids": [it.id, 999999]},
    )

    assert response.status_code == 404

    # Событие не должно остаться в БД, если теги не прошли проверку
    listed = await api_client.get(EVENTS_URL)
    assert _titles(listed.json()) == []


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"title": ""}, id="empty-title"),
        pytest.param({"title": "x" * 151}, id="title-too-long"),
        pytest.param({"location": ""}, id="empty-location"),
        pytest.param({"capacity": -1}, id="negative-capacity"),
        pytest.param({"event_date": "not-a-date"}, id="invalid-date"),
        pytest.param({"tag_ids": [0]}, id="non-positive-tag-id"),
        pytest.param({"tag_ids": "1"}, id="tag-ids-not-a-list"),
    ],
)
async def test_create_event_rejects_invalid_body(
    api_client: AsyncClient,
    make_user,
    changes: dict,
) -> None:
    organizer = await make_user(role=RoleName.ORGANIZER)

    response = await api_client.post(
        EVENTS_URL,
        headers=_auth_headers(organizer),
        json={**EVENT_BODY, **changes},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("missing_field", ["title", "location", "event_date", "capacity"])
async def test_create_event_requires_mandatory_fields(
    api_client: AsyncClient,
    make_user,
    missing_field: str,
) -> None:
    organizer = await make_user(role=RoleName.ORGANIZER)
    body = {key: value for key, value in EVENT_BODY.items() if key != missing_field}

    response = await api_client.post(
        EVENTS_URL,
        headers=_auth_headers(organizer),
        json=body,
    )

    assert response.status_code == 422
