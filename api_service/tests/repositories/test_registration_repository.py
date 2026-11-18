from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.dates import get_current_datetime
from src.core.uow import UnitOfWork
from src.models.registrations import Registration, RegistrationStatus


async def test_add_registration(
    uow: UnitOfWork,
    make_user,
    make_event,
):
    user = await make_user()
    event = await make_event()

    registration = await uow.registrations.add(
        Registration(
            user_id=user.id,
            event_id=event.id,
            status=RegistrationStatus.ACTIVE,
        )
    )

    assert registration.id is not None
    assert registration.user_id == user.id
    assert registration.event_id == event.id


async def test_get_by_user_and_event_returns_registration(
    uow: UnitOfWork,
    make_user,
    make_event,
):
    user = await make_user()
    event = await make_event()

    created = await uow.registrations.add(
        Registration(
            user_id=user.id,
            event_id=event.id,
            status=RegistrationStatus.ACTIVE,
        )
    )

    fetched = await uow.registrations.get_by_user_and_event(
        user.id,
        event.id,
    )

    assert fetched is not None
    assert fetched.id == created.id


async def test_get_by_user_and_event_returns_none_when_missing(
    uow: UnitOfWork,
    make_user,
    make_event,
):
    user = await make_user()
    event = await make_event()

    fetched = await uow.registrations.get_by_user_and_event(
        user.id,
        event.id,
    )

    assert fetched is None


async def test_get_by_user_id_returns_only_users_registrations(
    uow: UnitOfWork,
    make_user,
    make_event,
):
    user = await make_user()
    other_user = await make_user()

    first_event = await make_event(title="First")
    second_event = await make_event(title="Second")

    first = await uow.registrations.add(
        Registration(
            user_id=user.id,
            event_id=first_event.id,
            status=RegistrationStatus.ACTIVE,
        )
    )

    second = await uow.registrations.add(
        Registration(
            user_id=user.id,
            event_id=second_event.id,
            status=RegistrationStatus.ACTIVE,
        )
    )

    await uow.registrations.add(
        Registration(
            user_id=other_user.id,
            event_id=first_event.id,
            status=RegistrationStatus.ACTIVE,
        )
    )

    registrations = await uow.registrations.get_by_user_id(
        user.id
    )

    assert {registration.id for registration in registrations} == {
        first.id,
        second.id,
    }


async def test_count_active_for_event(
    uow: UnitOfWork,
    make_user,
    make_event,
):
    first_user = await make_user()
    second_user = await make_user()
    third_user = await make_user()

    event = await make_event()

    await uow.registrations.add(
        Registration(
            user_id=first_user.id,
            event_id=event.id,
            status=RegistrationStatus.ACTIVE,
        )
    )

    await uow.registrations.add(
        Registration(
            user_id=second_user.id,
            event_id=event.id,
            status=RegistrationStatus.ACTIVE,
        )
    )

    await uow.registrations.add(
        Registration(
            user_id=third_user.id,
            event_id=event.id,
            status=RegistrationStatus.CANCELLED,
        )
    )

    count = await uow.registrations.count_active_for_event(
        event.id
    )

    assert count == 2


async def test_get_event_participants_returns_only_active_users(
    uow: UnitOfWork,
    make_user,
    make_event,
):
    active_user = await make_user()
    cancelled_user = await make_user()

    event = await make_event()

    await uow.registrations.add(
        Registration(
            user_id=active_user.id,
            event_id=event.id,
            status=RegistrationStatus.ACTIVE,
        )
    )

    await uow.registrations.add(
        Registration(
            user_id=cancelled_user.id,
            event_id=event.id,
            status=RegistrationStatus.CANCELLED,
        )
    )

    participants = await uow.registrations.get_event_participants(
        event.id
    )

    assert {user.id for user in participants} == {
        active_user.id,
    }


async def test_duplicate_user_event_raises_integrity_error(
    uow: UnitOfWork,
    make_user,
    make_event,
):
    user = await make_user()
    event = await make_event()

    await uow.registrations.add(
        Registration(
            user_id=user.id,
            event_id=event.id,
            status=RegistrationStatus.ACTIVE,
        )
    )

    duplicate = Registration(
        user_id=user.id,
        event_id=event.id,
        status=RegistrationStatus.ACTIVE,
    )

    with pytest.raises(IntegrityError):
        await uow.registrations.add(duplicate)

    await uow.rollback()

async def test_list_visited_tag_ids_returns_tags_of_past_active_registrations(
    uow: UnitOfWork,
    make_user,
    make_event,
    make_tag,
):
    user = await make_user()
    now = get_current_datetime()

    it = await make_tag(name="IT")
    career = await make_tag(name="Career")
    sport = await make_tag(name="Sport")
    music = await make_tag(name="Music")

    past_event = await make_event(event_date=now - timedelta(days=10))
    another_past_event = await make_event(event_date=now - timedelta(days=5))
    future_event = await make_event(event_date=now + timedelta(days=5))
    cancelled_event = await make_event(event_date=now - timedelta(days=3))

    await uow.event_tags.add_tags(past_event.id, [it.id, career.id])
    await uow.event_tags.add_tags(another_past_event.id, [it.id])
    await uow.event_tags.add_tags(future_event.id, [sport.id])
    await uow.event_tags.add_tags(cancelled_event.id, [music.id])

    for event, status in (
        (past_event, RegistrationStatus.ACTIVE),
        (another_past_event, RegistrationStatus.ACTIVE),
        (future_event, RegistrationStatus.ACTIVE),
        (cancelled_event, RegistrationStatus.CANCELLED),
    ):
        await uow.registrations.add(
            Registration(user_id=user.id, event_id=event.id, status=status)
        )

    tag_ids = await uow.registrations.list_visited_tag_ids(user.id)

    # Тег IT встречается у двух мероприятий, но возвращается один раз
    assert sorted(tag_ids) == sorted([it.id, career.id])


async def test_list_visited_tag_ids_ignores_other_users(
    uow: UnitOfWork,
    make_user,
    make_event,
    make_tag,
):
    user = await make_user()
    other_user = await make_user()
    tag = await make_tag()

    event = await make_event(event_date=get_current_datetime() - timedelta(days=1))
    await uow.event_tags.add_tags(event.id, [tag.id])
    await uow.registrations.add(
        Registration(
            user_id=other_user.id,
            event_id=event.id,
            status=RegistrationStatus.ACTIVE,
        )
    )

    assert await uow.registrations.list_visited_tag_ids(user.id) == []


async def test_list_visited_tag_ids_filters_by_status(
    uow: UnitOfWork,
    make_user,
    make_event,
    make_tag,
):
    user = await make_user()
    past = get_current_datetime() - timedelta(days=1)

    active_tag = await make_tag()
    cancelled_tag = await make_tag()

    active_event = await make_event(event_date=past)
    cancelled_event = await make_event(event_date=past)

    await uow.event_tags.add_tags(active_event.id, [active_tag.id])
    await uow.event_tags.add_tags(cancelled_event.id, [cancelled_tag.id])

    await uow.registrations.add(
        Registration(
            user_id=user.id,
            event_id=active_event.id,
            status=RegistrationStatus.ACTIVE,
        )
    )
    await uow.registrations.add(
        Registration(
            user_id=user.id,
            event_id=cancelled_event.id,
            status=RegistrationStatus.CANCELLED,
        )
    )

    tag_ids = await uow.registrations.list_visited_tag_ids(
        user.id,
        status=RegistrationStatus.CANCELLED,
    )

    assert tag_ids == [cancelled_tag.id]


async def test_list_visited_tag_ids_respects_before(
    uow: UnitOfWork,
    make_user,
    make_event,
    make_tag,
):
    user = await make_user()
    now = get_current_datetime()

    early_tag = await make_tag()
    late_tag = await make_tag()

    early_event = await make_event(event_date=now - timedelta(days=10))
    late_event = await make_event(event_date=now - timedelta(days=2))

    await uow.event_tags.add_tags(early_event.id, [early_tag.id])
    await uow.event_tags.add_tags(late_event.id, [late_tag.id])

    for event in (early_event, late_event):
        await uow.registrations.add(
            Registration(
                user_id=user.id,
                event_id=event.id,
                status=RegistrationStatus.ACTIVE,
            )
        )

    tag_ids = await uow.registrations.list_visited_tag_ids(
        user.id,
        before=now - timedelta(days=5),
    )

    assert tag_ids == [early_tag.id]
