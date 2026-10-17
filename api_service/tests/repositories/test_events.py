from datetime import UTC, datetime, timedelta

from src.core.dates import get_current_datetime
from src.core.uow import UnitOfWork
from src.models.event_tags import EventTag
from src.models.events import Event
from src.models.registrations import Registration, RegistrationStatus
from src.models.tags import Tag


async def test_add_persists_event_and_assigns_id(make_event):
    title = "Hackathon"

    event = await make_event(title=title)

    assert event.id is not None
    assert event.title == title


async def test_get_by_id_returns_added_event(uow: UnitOfWork, make_event):
    event = await make_event()

    fetched = await uow.events.get_by_id(event.id)

    assert fetched is not None
    assert fetched.id == event.id


async def test_get_by_id_returns_none_for_missing_event(uow: UnitOfWork):
    assert await uow.events.get_by_id(999_999) is None


async def test_get_by_id_returns_none_for_deleted_event(uow: UnitOfWork, make_event):
    event = await make_event()
    event.deleted_at = datetime(2026, 1, 1, tzinfo=UTC)
    await uow.events.update(event)

    assert await uow.events.get_by_id(event.id) is None


async def test_get_by_id_with_tags_loads_relationship(uow: UnitOfWork, make_event, make_tag):
    event = await make_event()
    tag = await make_tag(name="IT")
    await uow.event_tags.add_tags(event.id, [tag.id])

    fetched = await uow.events.get_by_id(event.id, with_tags=True)

    assert fetched is not None
    tag_names = {event_tag.tag.name for event_tag in fetched.event_tags}
    assert tag_names == {tag.name}


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


async def test_list_filtered_loads_tags(uow: UnitOfWork, make_event, make_tag):
    event = await make_event()
    tag = await make_tag(name="IT")
    await uow.event_tags.add_tags(event.id, [tag.id])

    events = await uow.events.list_filtered()

    tag_names = {event_tag.tag.name for event_tag in events[0].event_tags}
    assert tag_names == {tag.name}


async def test_list_by_organizer_loads_tags(uow: UnitOfWork, make_event, make_tag):
    event = await make_event()
    tag = await make_tag(name="IT")
    await uow.event_tags.add_tags(event.id, [tag.id])

    events = await uow.events.list_by_organizer(event.created_by_id)

    tag_names = {event_tag.tag.name for event_tag in events[0].event_tags}
    assert tag_names == {tag.name}


async def test_list_by_organizer_returns_only_their_events(
    uow: UnitOfWork, make_user, make_event
):
    organizer = await make_user()
    own_event = await make_event(title="Own", created_by_id=organizer.id)
    await make_event(title="Someone else's")

    events = await uow.events.list_by_organizer(organizer.id)

    titles = {event.title for event in events}
    assert titles == {own_event.title}


async def test_list_filtered_by_tag_returns_expected_events(
    uow: UnitOfWork,
    seed_events: list[Event],
    seed_tags: list[Tag],
    seed_event_tags: list[EventTag],
):
    for tag in seed_tags:
        expected_ids = {
            event_tag.event_id
            for event_tag in seed_event_tags
            if event_tag.tag_id == tag.id
        }

        events = await uow.events.list_filtered(tag_ids=[tag.id])

        assert {event.id for event in events} == expected_ids, tag.name


async def test_get_by_id_returns_each_seeded_event(
    uow: UnitOfWork,
    seed_events: list[Event],
):
    for expected in seed_events:
        fetched = await uow.events.get_by_id(expected.id)

        assert fetched is not None
        assert fetched.title == expected.title


async def _register(
    uow: UnitOfWork,
    user_id: int,
    event_id: int,
    status: RegistrationStatus | None = None,
) -> None:
    await uow.registrations.add(
        Registration(
            user_id=user_id,
            event_id=event_id,
            status=status or RegistrationStatus.ACTIVE,
        )
    )


async def test_list_recommendation_candidates_returns_future_events_with_tags(
    uow: UnitOfWork, make_user, make_event, make_tag
):
    user = await make_user()
    now = get_current_datetime()
    tag_a = await make_tag()
    tag_b = await make_tag()

    tagged = await make_event(event_date=now + timedelta(days=1))
    untagged = await make_event(event_date=now + timedelta(days=2))
    await make_event(event_date=now - timedelta(days=1))
    await uow.event_tags.add_tags(tagged.id, [tag_a.id, tag_b.id])

    candidates = await uow.events.list_recommendation_candidates(user.id)

    assert [event_id for event_id, _ in candidates] == [tagged.id, untagged.id]
    assert sorted(candidates[0][1]) == sorted([tag_a.id, tag_b.id])
    assert candidates[1][1] == []


async def test_list_recommendation_candidates_sorted_by_date_then_id(
    uow: UnitOfWork, make_user, make_event
):
    user = await make_user()
    now = get_current_datetime()
    same_date = now + timedelta(days=3)

    late = await make_event(event_date=now + timedelta(days=5))
    first_same = await make_event(event_date=same_date)
    second_same = await make_event(event_date=same_date)
    early = await make_event(event_date=now + timedelta(days=1))

    candidates = await uow.events.list_recommendation_candidates(user.id)

    assert [event_id for event_id, _ in candidates] == [
        early.id,
        first_same.id,
        second_same.id,
        late.id,
    ]


async def test_list_recommendation_candidates_excludes_events_user_registered_for(
    uow: UnitOfWork, make_user, make_event
):
    user = await make_user()
    future = get_current_datetime() + timedelta(days=1)

    registered = await make_event(event_date=future)
    cancelled = await make_event(event_date=future)
    free = await make_event(event_date=future)

    await _register(uow, user.id, registered.id)
    await _register(uow, user.id, cancelled.id, RegistrationStatus.CANCELLED)

    candidates = await uow.events.list_recommendation_candidates(user.id)

    # После отмены регистрации мероприятие снова можно рекомендовать
    assert {event_id for event_id, _ in candidates} == {cancelled.id, free.id}
    assert registered.id not in {event_id for event_id, _ in candidates}


async def test_list_recommendation_candidates_excludes_full_events(
    uow: UnitOfWork, make_user, make_event
):
    user = await make_user()
    other = await make_user()
    another = await make_user()
    future = get_current_datetime() + timedelta(days=1)

    full = await make_event(event_date=future, capacity=1)
    with_cancelled = await make_event(event_date=future, capacity=1)
    zero_capacity = await make_event(event_date=future, capacity=0)

    await _register(uow, other.id, full.id)
    await _register(uow, another.id, with_cancelled.id, RegistrationStatus.CANCELLED)

    candidates = await uow.events.list_recommendation_candidates(user.id)

    assert [event_id for event_id, _ in candidates] == [with_cancelled.id]
    assert zero_capacity.id not in {event_id for event_id, _ in candidates}


async def test_list_recommendation_candidates_include_deleted(
    uow: UnitOfWork, make_user, make_event
):
    user = await make_user()
    event = await make_event(event_date=get_current_datetime() + timedelta(days=1))
    event.deleted_at = get_current_datetime()
    await uow.events.update(event)

    assert await uow.events.list_recommendation_candidates(user.id) == []

    candidates = await uow.events.list_recommendation_candidates(
        user.id,
        include_deleted=True,
    )
    assert [event_id for event_id, _ in candidates] == [event.id]


async def test_list_recommendation_candidates_respects_after(
    uow: UnitOfWork, make_user, make_event
):
    user = await make_user()
    now = get_current_datetime()

    past = await make_event(event_date=now - timedelta(days=5))
    soon = await make_event(event_date=now + timedelta(days=1))
    later = await make_event(event_date=now + timedelta(days=10))

    candidates = await uow.events.list_recommendation_candidates(
        user.id,
        after=now - timedelta(days=10),
    )
    assert [event_id for event_id, _ in candidates] == [past.id, soon.id, later.id]

    candidates = await uow.events.list_recommendation_candidates(
        user.id,
        after=now + timedelta(days=5),
    )
    assert [event_id for event_id, _ in candidates] == [later.id]


async def test_list_recommendation_candidates_respects_limit(
    uow: UnitOfWork, make_user, make_event
):
    user = await make_user()
    now = get_current_datetime()

    first = await make_event(event_date=now + timedelta(days=1))
    second = await make_event(event_date=now + timedelta(days=2))
    await make_event(event_date=now + timedelta(days=3))

    candidates = await uow.events.list_recommendation_candidates(user.id, limit=2)

    assert [event_id for event_id, _ in candidates] == [first.id, second.id]
