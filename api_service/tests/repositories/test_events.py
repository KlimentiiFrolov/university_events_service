from datetime import UTC, datetime

import pytest

from src.core.uow import UnitOfWork
from src.models.events import Event
from src.models.tags import Tag


async def test_add_persists_event_and_assigns_id(make_event):
    event = await make_event(title="Hackathon")

    assert event.id is not None
    assert event.title == "Hackathon"


async def test_get_by_id_returns_added_event(uow: UnitOfWork, make_event):
    event = await make_event()

    fetched = await uow.events.get_by_id(event.id)

    assert fetched is not None
    assert fetched.id == event.id


async def test_get_by_id_returns_none_for_missing_event(uow: UnitOfWork):
    assert await uow.events.get_by_id(999_999) is None


async def test_get_by_id_with_tags_loads_relationship(uow: UnitOfWork, make_event, make_tag):
    event = await make_event()
    tag = await make_tag(name="IT")
    await uow.event_tags.add_tags(event.id, [tag.id])

    fetched = await uow.events.get_by_id(event.id, with_tags=True)

    assert fetched is not None
    tag_names = {event_tag.tag.name for event_tag in fetched.event_tags}
    assert tag_names == {"IT"}


async def test_get_by_id_for_update_returns_event(uow: UnitOfWork, make_event):
    event = await make_event()

    fetched = await uow.events.get_by_id(event.id, for_update=True)

    assert fetched is not None
    assert fetched.id == event.id


async def test_list_filtered_by_date_range_excludes_events_outside_it(
    uow: UnitOfWork, make_event
):
    early = await make_event(
        title="Early",
        event_date=datetime(2026, 1, 1, tzinfo=UTC),
    )
    late = await make_event(
        title="Late",
        event_date=datetime(2026, 6, 1, tzinfo=UTC),
    )

    events = await uow.events.list_filtered(date_from=datetime(2026, 5, 1, tzinfo=UTC))

    titles = {event.title for event in events}
    assert late.title in titles
    assert early.title not in titles


async def test_list_filtered_by_tags_returns_only_tagged_events(
    uow: UnitOfWork, make_event, make_tag
):
    matching = await make_event(title="Matching")
    other = await make_event(title="Other")
    tag = await make_tag(name="IT")
    await uow.event_tags.add_tags(matching.id, [tag.id])

    events = await uow.events.list_filtered(tag_ids=[tag.id])

    titles = {event.title for event in events}
    assert matching.title in titles
    assert other.title not in titles


async def test_list_by_organizer_returns_only_their_events(
    uow: UnitOfWork, make_user, make_event
):
    organizer = await make_user()
    own_event = await make_event(title="Own", created_by_id=organizer.id)
    await make_event(title="Someone else's")

    events = await uow.events.list_by_organizer(organizer.id)

    titles = {event.title for event in events}
    assert titles == {own_event.title}


@pytest.mark.parametrize(
    "tag_index,expected_titles",
    [
        pytest.param(0, {"Lecture", "Hackathon"}),  # IT
        pytest.param(1, {"Hackathon"}),  # Career
        pytest.param(2, {"Workshop"}),  # Sport
    ],
)
async def test_list_filtered_by_tag_returns_expected_events(
    uow: UnitOfWork,
    seed_events: list[Event],
    seed_tags: list[Tag],
    seed_event_tags,
    tag_index: int,
    expected_titles: set[str],
):
    tag = seed_tags[tag_index]

    events = await uow.events.list_filtered(tag_ids=[tag.id])

    assert {event.title for event in events} == expected_titles


@pytest.mark.parametrize(
    "event_index",
    [0, 1, 2],
)
async def test_get_by_id_returns_each_seeded_event(
    uow: UnitOfWork,
    seed_events: list[Event],
    event_index: int,
):
    expected = seed_events[event_index]

    fetched = await uow.events.get_by_id(expected.id)

    assert fetched is not None
    assert fetched.title == expected.title
