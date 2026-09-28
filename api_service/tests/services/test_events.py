from datetime import UTC, datetime

import pytest

from src.models.registrations import RegistrationStatus
from src.schemas.events import CreateEventSchema, UpdateEventSchema
from src.schemas.exceptions.domain import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from src.services.events import EventService
from src.services.registrations import RegistrationService


async def test_create_event_persists_event(
    event_service: EventService,
    make_user,
):
    organizer = await make_user()

    event = await event_service.create_event(
        organizer.id,
        CreateEventSchema(
            title="Lecture",
            location="Room 101",
            event_date=datetime(2026, 1, 10, tzinfo=UTC),
            capacity=30,
        ),
    )

    assert event.id is not None
    assert event.title == "Lecture"
    assert event.created_by_id == organizer.id


async def test_create_event_without_tags_succeeds(
    event_service: EventService,
    make_user,
):
    organizer = await make_user()

    event = await event_service.create_event(
        organizer.id,
        CreateEventSchema(
            title="Lecture",
            location="Room 101",
            event_date=datetime(2026, 1, 10, tzinfo=UTC),
            capacity=30,
        ),
    )

    fetched = await event_service.get_event(event.id)

    assert fetched.event_tags == []


async def test_create_event_with_tags_attaches_them(
    event_service: EventService,
    make_user,
    make_tag,
):
    organizer = await make_user()
    tag = await make_tag(name="IT")

    event = await event_service.create_event(
        organizer.id,
        CreateEventSchema(
            title="Hackathon",
            location="Main Hall",
            event_date=datetime(2026, 2, 1, tzinfo=UTC),
            capacity=50,
            tag_ids=[tag.id],
        ),
    )

    fetched = await event_service.get_event(event.id)
    tag_names = {event_tag.tag.name for event_tag in fetched.event_tags}

    assert tag_names == {"IT"}


async def test_create_event_missing_organizer_raises_not_found(
    event_service: EventService,
):
    with pytest.raises(NotFoundError):
        await event_service.create_event(
            999_999,
            CreateEventSchema(
                title="Lecture",
                location="Room 101",
                event_date=datetime(2026, 1, 10, tzinfo=UTC),
                capacity=30,
            ),
        )


async def test_create_event_missing_tag_raises_not_found(
    event_service: EventService,
    make_user,
):
    organizer = await make_user()

    with pytest.raises(NotFoundError):
        await event_service.create_event(
            organizer.id,
            CreateEventSchema(
                title="Lecture",
                location="Room 101",
                event_date=datetime(2026, 1, 10, tzinfo=UTC),
                capacity=30,
                tag_ids=[999_999],
            ),
        )


async def test_get_event_returns_event_with_tags_by_default(
    event_service: EventService,
    make_event,
    make_tag,
):
    event = await make_event()
    tag = await make_tag(name="IT")
    await event_service.uow.event_tags.add_tags(event.id, [tag.id])

    fetched = await event_service.get_event(event.id)
    tag_names = {event_tag.tag.name for event_tag in fetched.event_tags}

    assert tag_names == {"IT"}


async def test_get_event_raises_not_found_for_missing_event(
    event_service: EventService,
):
    with pytest.raises(NotFoundError):
        await event_service.get_event(999_999)


async def test_list_events_filters_by_date_range(
    event_service: EventService,
    make_event,
):
    early = await make_event(
        title="Early",
        event_date=datetime(2026, 1, 1, tzinfo=UTC),
    )
    late = await make_event(
        title="Late",
        event_date=datetime(2026, 6, 1, tzinfo=UTC),
    )

    events = await event_service.list_events(
        date_from=datetime(2026, 5, 1, tzinfo=UTC),
    )

    titles = {event.title for event in events}
    assert late.title in titles
    assert early.title not in titles


async def test_list_events_filters_by_tag(
    event_service: EventService,
    make_event,
    make_tag,
):
    matching = await make_event(title="Matching")
    other = await make_event(title="Other")
    tag = await make_tag(name="IT")
    await event_service.uow.event_tags.add_tags(matching.id, [tag.id])

    events = await event_service.list_events(tag_ids=[tag.id])

    titles = {event.title for event in events}
    assert matching.title in titles
    assert other.title not in titles


async def test_list_events_respects_pagination(
    event_service: EventService,
    make_event,
):
    await make_event(title="First", event_date=datetime(2026, 1, 1, tzinfo=UTC))
    await make_event(title="Second", event_date=datetime(2026, 1, 2, tzinfo=UTC))
    await make_event(title="Third", event_date=datetime(2026, 1, 3, tzinfo=UTC))

    first_page = await event_service.list_events(limit=2, offset=0)
    second_page = await event_service.list_events(limit=2, offset=2)

    assert [event.title for event in first_page] == ["First", "Second"]
    assert [event.title for event in second_page] == ["Third"]


async def test_list_organizer_events_returns_only_own_events(
    event_service: EventService,
    make_user,
    make_event,
):
    organizer = await make_user()
    own_event = await make_event(title="Own", created_by_id=organizer.id)
    await make_event(title="Someone else's")

    events = await event_service.list_organizer_events(organizer.id)

    titles = {event.title for event in events}
    assert titles == {own_event.title}


async def test_update_event_updates_fields(
    event_service: EventService,
    make_event,
):
    event = await make_event(title="Old title")

    updated = await event_service.update_event(
        event.id,
        event.created_by_id,
        UpdateEventSchema(title="New title"),
    )

    assert updated.title == "New title"


async def test_update_event_raises_forbidden_for_non_owner(
    event_service: EventService,
    make_event,
    make_user,
):
    event = await make_event()
    other_organizer = await make_user()

    with pytest.raises(ForbiddenError):
        await event_service.update_event(
            event.id,
            other_organizer.id,
            UpdateEventSchema(title="New title"),
        )


async def test_update_event_raises_not_found_for_missing_event(
    event_service: EventService,
    make_user,
):
    organizer = await make_user()

    with pytest.raises(NotFoundError):
        await event_service.update_event(
            999_999,
            organizer.id,
            UpdateEventSchema(title="New title"),
        )


async def test_update_event_capacity_below_active_registrations_raises_conflict(
    event_service: EventService,
    registration_service: RegistrationService,
    make_event,
    make_user,
):
    event = await make_event(capacity=5)
    participant = await make_user()

    await registration_service.register(participant.id, event.id)

    with pytest.raises(ConflictError):
        await event_service.update_event(
            event.id,
            event.created_by_id,
            UpdateEventSchema(capacity=0),
        )


async def test_set_event_tags_replaces_full_set(
    event_service: EventService,
    make_event,
    make_tag,
):
    event = await make_event()
    old_tag = await make_tag(name="Old")
    new_tag = await make_tag(name="New")
    await event_service.uow.event_tags.add_tags(event.id, [old_tag.id])

    updated = await event_service.set_event_tags(
        event.id,
        event.created_by_id,
        [new_tag.id],
    )

    tag_names = {event_tag.tag.name for event_tag in updated.event_tags}
    assert tag_names == {"New"}


async def test_set_event_tags_raises_forbidden_for_non_owner(
    event_service: EventService,
    make_event,
    make_user,
    make_tag,
):
    event = await make_event()
    other_organizer = await make_user()
    tag = await make_tag()

    with pytest.raises(ForbiddenError):
        await event_service.set_event_tags(
            event.id,
            other_organizer.id,
            [tag.id],
        )


async def test_set_event_tags_raises_not_found_for_missing_tag(
    event_service: EventService,
    make_event,
):
    event = await make_event()

    with pytest.raises(NotFoundError):
        await event_service.set_event_tags(
            event.id,
            event.created_by_id,
            [999_999],
        )


async def test_delete_event_hides_event_from_organizer_listing(
    event_service: EventService,
    make_event,
):
    event = await make_event()

    await event_service.delete_event(event.id, event.created_by_id)

    events = await event_service.list_organizer_events(event.created_by_id)

    assert event.id not in {listed.id for listed in events}


async def test_delete_event_cancels_active_registrations(
    event_service: EventService,
    registration_service: RegistrationService,
    make_event,
    make_user,
):
    event = await make_event()
    participant = await make_user()

    await registration_service.register(participant.id, event.id)

    await event_service.delete_event(event.id, event.created_by_id)

    registrations = await registration_service.get_my_registrations(participant.id)

    assert registrations[0].status == RegistrationStatus.CANCELLED


async def test_delete_event_raises_forbidden_for_non_owner(
    event_service: EventService,
    make_event,
    make_user,
):
    event = await make_event()
    other_organizer = await make_user()

    with pytest.raises(ForbiddenError):
        await event_service.delete_event(event.id, other_organizer.id)


async def test_delete_event_raises_not_found_for_missing_event(
    event_service: EventService,
    make_user,
):
    organizer = await make_user()

    with pytest.raises(NotFoundError):
        await event_service.delete_event(999_999, organizer.id)
