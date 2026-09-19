from datetime import datetime, timezone

from src.models.events import Event
from src.models.registrations import (
    Registration,
    RegistrationStatus,
)
from src.models.users import User
from src.repositories.registrations import RegistrationRepository
from src.schemas.exceptions.domain import (
    EventCapacityExceededError,
    NotFoundError,
    RegistrationAlreadyActiveError,
    RegistrationAlreadyCancelledError,
    RegistrationAlreadyExistsError,
)


class RegistrationService:
    def __init__(
        self,
        repository: RegistrationRepository,
    ):
        self.repository = repository

    async def _get_user(
        self,
        user_id: int,
    ) -> User:
        user = await self.repository.get_user(user_id)

        if user is None:
            raise NotFoundError("User", user_id)

        return user

    async def _get_event(
        self,
        event_id: int,
    ) -> Event:
        event = await self.repository.get_event(event_id)

        if event is None:
            raise NotFoundError("Event", event_id)

        return event

    async def _check_capacity(
        self,
        event: Event,
    ) -> None:
        participants_count = (
            await self.repository.count_active_for_event(
                event.id
            )
        )

        if participants_count >= event.capacity:
            raise EventCapacityExceededError(
                f"Event id={event.id} has no free places"
            )

    async def register(
        self,
        user_id: int,
        event_id: int,
    ) -> Registration:
        await self._get_user(user_id)
        event = await self._get_event(event_id)

        existing = (
            await self.repository.get_by_user_and_event(
                user_id,
                event_id,
            )
        )

        if existing is not None:
            raise RegistrationAlreadyExistsError(
                "Registration already exists"
            )

        await self._check_capacity(event)

        registration = Registration(
            user_id=user_id,
            event_id=event_id,
            status=RegistrationStatus.ACTIVE,
        )

        return await self.repository.add(registration)

    async def cancel(
        self,
        user_id: int,
        event_id: int,
    ) -> Registration:
        registration = (
            await self.repository.get_by_user_and_event(
                user_id,
                event_id,
            )
        )

        if registration is None:
            raise NotFoundError(
                "Registration",
                f"user_id={user_id}, event_id={event_id}",
            )

        if registration.status == RegistrationStatus.CANCELLED:
            raise RegistrationAlreadyCancelledError(
                "Registration is already cancelled"
            )

        registration.status = RegistrationStatus.CANCELLED
        registration.cancelled_at = datetime.now(timezone.utc)

        return await self.repository.update(registration)

    async def reregister(
        self,
        user_id: int,
        event_id: int,
    ) -> Registration:
        registration = (
            await self.repository.get_by_user_and_event(
                user_id,
                event_id,
            )
        )

        if registration is None:
            raise NotFoundError(
                "Registration",
                f"user_id={user_id}, event_id={event_id}",
            )

        if registration.status == RegistrationStatus.ACTIVE:
            raise RegistrationAlreadyActiveError(
                "Registration is already active"
            )

        event = await self._get_event(event_id)

        await self._check_capacity(event)

        registration.status = RegistrationStatus.ACTIVE
        registration.registered_at = datetime.now(timezone.utc)
        registration.cancelled_at = None

        return await self.repository.update(registration)

    async def get_my_registrations(
        self,
        user_id: int,
    ) -> list[Registration]:
        await self._get_user(user_id)

        return await self.repository.get_by_user_id(user_id)

    async def get_event_participants(
        self,
        event_id: int,
    ) -> list[User]:
        await self._get_event(event_id)

        return await self.repository.get_event_participants(
            event_id
        )