import pytest

from src.models.registrations import RegistrationStatus
from src.schemas.exceptions.domain import (
    EventCapacityExceededError,
    NotFoundError,
    RegistrationAlreadyActiveError,
    RegistrationAlreadyCancelledError,
    RegistrationAlreadyExistsError,
)
from src.services.registrations import RegistrationService


async def test_register_creates_active_registration(
    registration_service: RegistrationService,
    make_user,
    make_event,
):
    user = await make_user()
    event = await make_event()

    registration = await registration_service.register(
        user.id,
        event.id,
    )

    assert registration.id is not None
    assert registration.user_id == user.id
    assert registration.event_id == event.id
    assert registration.status == RegistrationStatus.ACTIVE
    assert registration.cancelled_at is None


async def test_register_missing_user_raises_not_found(
    registration_service: RegistrationService,
    make_event,
):
    event = await make_event()

    with pytest.raises(NotFoundError):
        await registration_service.register(
            999_999,
            event.id,
        )


async def test_register_missing_event_raises_not_found(
    registration_service: RegistrationService,
    make_user,
):
    user = await make_user()

    with pytest.raises(NotFoundError):
        await registration_service.register(
            user.id,
            999_999,
        )


async def test_duplicate_registration_raises_error(
    registration_service: RegistrationService,
    make_user,
    make_event,
):
    user = await make_user()
    event = await make_event()

    await registration_service.register(user.id, event.id)

    with pytest.raises(RegistrationAlreadyExistsError):
        await registration_service.register(user.id, event.id)


async def test_register_when_capacity_is_full_raises_error(
    registration_service: RegistrationService,
    make_user,
    make_event,
):
    event = await make_event(capacity=1)

    first_user = await make_user()
    second_user = await make_user()

    await registration_service.register(first_user.id, event.id)

    with pytest.raises(EventCapacityExceededError):
        await registration_service.register(
            second_user.id,
            event.id,
        )


async def test_cancel_registration(
    registration_service: RegistrationService,
    make_user,
    make_event,
):
    user = await make_user()
    event = await make_event()

    await registration_service.register(user.id, event.id)

    registration = await registration_service.cancel(
        user.id,
        event.id,
    )

    assert registration.status == RegistrationStatus.CANCELLED
    assert registration.cancelled_at is not None


async def test_cancel_missing_registration_raises_not_found(
    registration_service: RegistrationService,
    make_user,
    make_event,
):
    user = await make_user()
    event = await make_event()

    with pytest.raises(NotFoundError):
        await registration_service.cancel(
            user.id,
            event.id,
        )


async def test_cancel_already_cancelled_registration_raises_error(
    registration_service: RegistrationService,
    make_user,
    make_event,
):
    user = await make_user()
    event = await make_event()

    await registration_service.register(user.id, event.id)
    await registration_service.cancel(user.id, event.id)

    with pytest.raises(RegistrationAlreadyCancelledError):
        await registration_service.cancel(
            user.id,
            event.id,
        )


async def test_reregister_cancelled_registration(
    registration_service: RegistrationService,
    make_user,
    make_event,
):
    user = await make_user()
    event = await make_event()

    await registration_service.register(user.id, event.id)
    await registration_service.cancel(user.id, event.id)

    registration = await registration_service.reregister(
        user.id,
        event.id,
    )

    assert registration.status == RegistrationStatus.ACTIVE
    assert registration.cancelled_at is None


async def test_reregister_active_registration_raises_error(
    registration_service: RegistrationService,
    make_user,
    make_event,
):
    user = await make_user()
    event = await make_event()

    await registration_service.register(user.id, event.id)

    with pytest.raises(RegistrationAlreadyActiveError):
        await registration_service.reregister(
            user.id,
            event.id,
        )


async def test_get_my_registrations_returns_only_users_registrations(
    registration_service: RegistrationService,
    make_user,
    make_event,
):
    user = await make_user()
    other_user = await make_user()

    first_event = await make_event(title="First")
    second_event = await make_event(title="Second")

    await registration_service.register(user.id, first_event.id)
    await registration_service.register(user.id, second_event.id)
    await registration_service.register(other_user.id, first_event.id)

    registrations = await registration_service.get_my_registrations(
        user.id
    )

    assert len(registrations) == 2
    assert {registration.event_id for registration in registrations} == {
        first_event.id,
        second_event.id,
    }


async def test_get_event_participants_returns_only_active_users(
    registration_service: RegistrationService,
    make_user,
    make_event,
):
    first_user = await make_user()
    second_user = await make_user()

    event = await make_event()

    await registration_service.register(first_user.id, event.id)
    await registration_service.register(second_user.id, event.id)

    await registration_service.cancel(second_user.id, event.id)

    participants = await registration_service.get_event_participants(
        event.id
    )

    assert {user.id for user in participants} == {first_user.id}