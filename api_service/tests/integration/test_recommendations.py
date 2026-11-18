from collections.abc import Callable
from datetime import timedelta

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from dependencies import get_recommendation_client
from src.core.dates import get_current_datetime
from src.core.tokens import create_access_token
from src.models.roles import RoleName
from src.models.users import User
from src.schemas.exceptions.domain import RecommendationUnavailableError

RECOMMENDATIONS_URL = "/api/v1/events/recommendations"


class FakeRecommendationClient:
    def __init__(self):
        self.event_ids: list[int] = []
        self.error: Exception | None = None
        self.limits: list[int] = []

    async def recommend(self, visited_tag_ids, candidates, limit) -> list[int]:
        self.limits.append(limit)
        if self.error is not None:
            raise self.error
        return self.event_ids


@pytest.fixture
def fake_client(test_app: FastAPI) -> FakeRecommendationClient:
    client = FakeRecommendationClient()
    test_app.dependency_overrides[get_recommendation_client] = lambda: client
    return client


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def future_event(make_event) -> Callable:
    async def _future_event(title: str):
        return await make_event(
            title=title,
            event_date=get_current_datetime() + timedelta(days=1),
        )

    return _future_event


async def test_returns_events_in_recommended_order(
    api_client: AsyncClient,
    fake_client: FakeRecommendationClient,
    make_user,
    future_event,
):
    user = await make_user()
    first = await future_event("First")
    second = await future_event("Second")
    fake_client.event_ids = [second.id, first.id]

    response = await api_client.get(RECOMMENDATIONS_URL, headers=_auth_headers(user))

    assert response.status_code == 200
    assert [event["id"] for event in response.json()["items"]] == [second.id, first.id]


async def test_passes_limit_to_client(
    api_client: AsyncClient,
    fake_client: FakeRecommendationClient,
    make_user,
    future_event,
):
    user = await make_user()
    await future_event("Event")

    response = await api_client.get(
        RECOMMENDATIONS_URL,
        params={"limit": 3},
        headers=_auth_headers(user),
    )

    assert response.status_code == 200
    assert fake_client.limits == [3]


async def test_returns_empty_list_without_candidates(
    api_client: AsyncClient,
    fake_client: FakeRecommendationClient,
    make_user,
):
    user = await make_user()

    response = await api_client.get(RECOMMENDATIONS_URL, headers=_auth_headers(user))

    assert response.status_code == 200
    assert response.json() == {"items": []}
    assert fake_client.limits == []


async def test_returns_503_when_service_unavailable(
    api_client: AsyncClient,
    fake_client: FakeRecommendationClient,
    make_user,
    future_event,
):
    user = await make_user()
    await future_event("Event")
    fake_client.error = RecommendationUnavailableError("down")

    response = await api_client.get(RECOMMENDATIONS_URL, headers=_auth_headers(user))

    assert response.status_code == 503


async def test_requires_authentication(
    api_client: AsyncClient,
    fake_client: FakeRecommendationClient,
):
    response = await api_client.get(RECOMMENDATIONS_URL)

    assert response.status_code == 401


async def test_forbidden_for_organizer(
    api_client: AsyncClient,
    fake_client: FakeRecommendationClient,
    make_user,
):
    organizer = await make_user(role=RoleName.ORGANIZER)

    response = await api_client.get(RECOMMENDATIONS_URL, headers=_auth_headers(organizer))

    assert response.status_code == 403


@pytest.mark.parametrize("limit", [0, 101])
async def test_rejects_limit_out_of_range(
    api_client: AsyncClient,
    fake_client: FakeRecommendationClient,
    make_user,
    limit: int,
):
    user = await make_user()

    response = await api_client.get(
        RECOMMENDATIONS_URL,
        params={"limit": limit},
        headers=_auth_headers(user),
    )

    assert response.status_code == 422
