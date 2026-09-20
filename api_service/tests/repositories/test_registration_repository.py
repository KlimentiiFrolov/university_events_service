import pytest
from sqlalchemy.exc import IntegrityError

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