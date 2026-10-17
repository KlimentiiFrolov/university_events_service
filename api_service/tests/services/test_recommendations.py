from datetime import timedelta

import pytest

from src.core.dates import get_current_datetime
from src.core.uow import UnitOfWork
from src.models.registrations import Registration, RegistrationStatus
from src.schemas.exceptions.domain import RecommendationUnavailableError
from src.services.recommendations import RecommendationService


class FakeRecommendationClient:
    def __init__(self, event_ids: list[int] | None = None, error: Exception | None = None):
        self.event_ids = event_ids or []
        self.error = error
        self.calls: list[tuple[list[int], list[tuple[int, list[int]]], int]] = []

    async def recommend(self, visited_tag_ids, candidates, limit) -> list[int]:
        self.calls.append((visited_tag_ids, candidates, limit))
        if self.error is not None:
            raise self.error
        return self.event_ids


def make_service(uow: UnitOfWork, client: FakeRecommendationClient, **kwargs):
    return RecommendationService(uow=uow, client=client, **kwargs)

async def test_recommend_events_passes_history_and_candidates_to_client(
    uow: UnitOfWork, make_user, make_event, make_tag
):
    user = await make_user()
    now = get_current_datetime()
    tag = await make_tag()

    visited = await make_event(event_date=now - timedelta(days=1))
    candidate = await make_event(event_date=now + timedelta(days=1))
    await uow.event_tags.add_tags(visited.id, [tag.id])
    await uow.event_tags.add_tags(candidate.id, [tag.id])
    await uow.registrations.add(
        Registration(user_id=user.id, event_id=visited.id, status=RegistrationStatus.ACTIVE)
    )

    client = FakeRecommendationClient()
    await make_service(uow, client).recommend_events(user.id, limit=5)

    assert client.calls == [([tag.id], [(candidate.id, [tag.id])], 5)]


async def test_recommend_events_keeps_client_order_and_skips_missing(
    uow: UnitOfWork, make_user, make_event, make_tag
):
    user = await make_user()
    future = get_current_datetime() + timedelta(days=1)
    tag = await make_tag()

    first = await make_event(event_date=future)
    second = await make_event(event_date=future)
    await uow.event_tags.add_tags(second.id, [tag.id])

    client = FakeRecommendationClient(event_ids=[second.id, 999_999, first.id])
    events = await make_service(uow, client).recommend_events(user.id, limit=5)

    assert [event.id for event in events] == [second.id, first.id]
    assert [t.id for t in events[0].tags] == [tag.id]
    assert events[1].tags == []


async def test_recommend_events_without_candidates_does_not_call_client(
    uow: UnitOfWork, make_user, make_event
):
    user = await make_user()
    await make_event(event_date=get_current_datetime() - timedelta(days=1))

    client = FakeRecommendationClient()
    events = await make_service(uow, client).recommend_events(user.id, limit=5)

    assert events == []
    assert client.calls == []


async def test_recommend_events_limits_candidates(uow: UnitOfWork, make_user, make_event):
    user = await make_user()
    now = get_current_datetime()

    nearest = await make_event(event_date=now + timedelta(days=1))
    await make_event(event_date=now + timedelta(days=2))

    client = FakeRecommendationClient()
    await make_service(uow, client, max_candidates=1).recommend_events(user.id, limit=5)

    assert len(client.calls) == 1
    _, candidates, _ = client.calls[0]
    assert candidates == [(nearest.id, [])]


async def test_recommend_events_propagates_client_error(
    uow: UnitOfWork, make_user, make_event
):
    user = await make_user()
    await make_event(event_date=get_current_datetime() + timedelta(days=1))

    client = FakeRecommendationClient(error=RecommendationUnavailableError("down"))

    with pytest.raises(RecommendationUnavailableError):
        await make_service(uow, client).recommend_events(user.id, limit=5)
