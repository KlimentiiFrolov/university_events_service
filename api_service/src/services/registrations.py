from src.core.dates import get_current_datetime
from src.core.logger import log
from src.core.uow import UnitOfWork
from src.models.events import Event
from src.models.registrations import (
    Registration,
    RegistrationStatus,
)
from src.models.users import User
from src.schemas.exceptions.domain import (
    EventCapacityExceededError,
    ForbiddenError,
    NotFoundError,
    RegistrationAlreadyActiveError,
    RegistrationAlreadyCancelledError,
    RegistrationAlreadyExistsError,
)

class RegistrationService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def _get_user(
        self,
        user_id: int,
    ) -> User:
        user = await self.uow.users.get_by_id(user_id)

        if user is None:
            log.warning("User id=%d not found", user_id)
            raise NotFoundError("User", user_id)

        log.debug("User id=%d found", user_id)
        return user

    async def _get_event(
        self,
        event_id: int,
        for_update: bool = False,
    ) -> Event:
        event = await self.uow.events.get_by_id(event_id, for_update=for_update)

        if event is None:
            log.warning("Event id=%d not found", event_id)
            raise NotFoundError("Event", event_id)

        log.debug("Event id=%d found (for_update=%s)", event_id, for_update)
        return event

    def _ensure_event_owner(
            self,
            event: Event,
            organizer_id: int,
    ) -> None:
        if event.created_by_id != organizer_id:
            log.warning(
                "User id=%d is not the organizer of event id=%d",
                organizer_id,
                event.id,
            )
            raise ForbiddenError(
                f"User id={organizer_id} is not the organizer "
                f"of event id={event.id}"
            )

    async def _get_registration(
        self,
        user_id: int,
        event_id: int,
    ) -> Registration:
        registration = (
            await self.uow.registrations.get_by_user_and_event(
                user_id,
                event_id,
            )
        )

        if registration is None:
            log.warning(
                "Registration of user id=%d on event id=%d not found",
                user_id, event_id,
            )
            raise NotFoundError(
                "Registration",
                f"user_id={user_id}, event_id={event_id}",
            )

        return registration

    async def _check_capacity(
        self,
        event: Event,
    ) -> None:
        participants_count = (
            await self.uow.registrations.count_active_for_event(
                event.id
            )
        )

        if participants_count >= event.capacity:
            log.warning(
                "Event id=%d has no free places (active=%d, capacity=%d)",
                event.id, participants_count, event.capacity,
            )
            raise EventCapacityExceededError(
                f"Event id={event.id} has no free places"
            )

        log.debug(
            "Event id=%d has free places (active=%d, capacity=%d)",
            event.id, participants_count, event.capacity,
        )

    async def register(
        self,
        user_id: int,
        event_id: int,
    ) -> Registration:
        await self._get_user(user_id)
        event = await self._get_event(event_id, for_update=True)

        existing = (
            await self.uow.registrations.get_by_user_and_event(
                user_id,
                event_id,
            )
        )

        if existing is not None:
            log.warning(
                "Registration of user id=%d on event id=%d already exists (status=%s)",
                user_id, event_id, existing.status,
            )
            raise RegistrationAlreadyExistsError(
                "Registration already exists"
            )

        await self._check_capacity(event)

        registration = Registration(
            user_id=user_id,
            event_id=event_id,
            status=RegistrationStatus.ACTIVE,
        )

        registration = await self.uow.registrations.add(registration)

        log.info("User id=%d registered on event id=%d", user_id, event_id)
        return registration

    async def cancel(
        self,
        user_id: int,
        event_id: int,
    ) -> Registration:
        registration = await self._get_registration(user_id, event_id)

        if registration.status == RegistrationStatus.CANCELLED:
            log.warning(
                "Registration of user id=%d on event id=%d is already cancelled",
                user_id, event_id,
            )
            raise RegistrationAlreadyCancelledError(
                "Registration is already cancelled"
            )

        registration.status = RegistrationStatus.CANCELLED
        registration.cancelled_at = get_current_datetime()

        registration = await self.uow.registrations.update(registration)

        log.info("User id=%d cancelled registration on event id=%d", user_id, event_id)
        return registration

    async def reregister(
        self,
        user_id: int,
        event_id: int,
    ) -> Registration:
        registration = await self._get_registration(user_id, event_id)

        if registration.status == RegistrationStatus.ACTIVE:
            log.warning(
                "Registration of user id=%d on event id=%d is already active",
                user_id, event_id,
            )
            raise RegistrationAlreadyActiveError(
                "Registration is already active"
            )

        event = await self._get_event(event_id, for_update=True)

        await self._check_capacity(event)

        registration.status = RegistrationStatus.ACTIVE
        registration.registered_at = get_current_datetime()
        registration.cancelled_at = None

        registration = await self.uow.registrations.update(registration)

        log.info("User id=%d re-registered on event id=%d", user_id, event_id)
        return registration

    async def get_my_registrations(
        self,
        user_id: int,
    ) -> list[Registration]:
        await self._get_user(user_id) # TODO: можно будет убрать эту проверку, после того, как сделаем слой представлений и добавим зависимость для авторизации пользователя

        registrations = await self.uow.registrations.get_by_user_id(user_id)

        log.debug("Listed %d registrations of user id=%d", len(registrations), user_id)
        return registrations

    async def get_event_participants(
            self,
            event_id: int,
            organizer_id: int,
    ) -> list[User]:
        event = await self._get_event(event_id)

        self._ensure_event_owner(
            event,
            organizer_id,
        )

        participants = (
            await self.uow.registrations.get_event_participants(
                event_id
            )
        )

        log.debug(
            "Listed %d participants of event id=%d",
            len(participants),
            event_id,
        )

        return participants
