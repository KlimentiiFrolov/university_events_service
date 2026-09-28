from datetime import datetime

from src.core.dates import get_current_datetime
from src.core.uow import UnitOfWork
from src.models.events import Event
from src.schemas.events import CreateEventSchema, UpdateEventSchema
from src.schemas.exceptions.domain import ConflictError, ForbiddenError, NotFoundError


class EventService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def _get_event(
        self,
        event_id: int,
        *,
        with_tags: bool = False,
    ) -> Event:
        event = await self.uow.events.get_by_id(event_id, with_tags=with_tags)

        if event is None:
            raise NotFoundError("Event", event_id)

        return event

    def _ensure_owner(self, event: Event, organizer_id: int) -> None:
        if event.created_by_id != organizer_id:
            raise ForbiddenError(
                f"User id={organizer_id} is not the organizer of event id={event.id}"
            )

    async def _validate_tag_ids(self, tag_ids: list[int]) -> None:
        tags = await self.uow.tags.list_by_ids(tag_ids)
        missing = set(tag_ids) - {tag.id for tag in tags}

        if missing:
            raise NotFoundError(
                "Tag",
                ", ".join(str(tag_id) for tag_id in sorted(missing)),
            )

    async def _validate_capacity(self, event_id: int, capacity: int) -> None:
        active_count = await self.uow.registrations.count_active_for_event(event_id)

        if capacity < active_count:
            raise ConflictError(
                f"Cannot set capacity={capacity} below "
                f"active registrations count={active_count}"
            )

    async def create_event(
        self,
        organizer_id: int,
        data: CreateEventSchema,
    ) -> Event:
        organizer = await self.uow.users.get_by_id(organizer_id)

        if organizer is None:
            raise NotFoundError("User", organizer_id)

        tag_ids = data.tag_ids or []
        await self._validate_tag_ids(tag_ids)

        event = await self.uow.events.add(
            Event(
                **data.model_dump(exclude={"tag_ids"}),
                created_by_id=organizer_id,
            )
        )

        await self.uow.event_tags.add_tags(event.id, tag_ids)

        return event

    async def get_event(
        self,
        event_id: int,
        *,
        with_tags: bool = True,
    ) -> Event:
        return await self._get_event(event_id, with_tags=with_tags)

    async def list_events(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        tag_ids: list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Event]:
        return await self.uow.events.list_filtered(
            date_from=date_from,
            date_to=date_to,
            tag_ids=tag_ids,
            limit=limit,
            offset=offset,
        )

    async def list_organizer_events(
        self,
        organizer_id: int,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Event]:
        return await self.uow.events.list_by_organizer(
            organizer_id,
            limit=limit,
            offset=offset,
        )

    async def update_event(
        self,
        event_id: int,
        organizer_id: int,
        data: UpdateEventSchema,
    ) -> Event:
        event = await self._get_event(event_id)
        self._ensure_owner(event, organizer_id)

        if data.capacity is not None:
            await self._validate_capacity(event_id, data.capacity)

        updates = data.model_dump(exclude_none=True)

        for field, value in updates.items():
            setattr(event, field, value)

        return await self.uow.events.update(event)

    async def set_event_tags(
        self,
        event_id: int,
        organizer_id: int,
        tag_ids: list[int],
    ) -> Event:
        event = await self._get_event(event_id)
        self._ensure_owner(event, organizer_id)

        if tag_ids:
            await self._validate_tag_ids(tag_ids)

        await self.uow.event_tags.replace_tags(event_id, tag_ids)

        return await self._get_event(event_id, with_tags=True)

    async def delete_event(
        self,
        event_id: int,
        organizer_id: int,
    ) -> None:
        event = await self._get_event(event_id)
        self._ensure_owner(event, organizer_id)

        await self.uow.registrations.cancel_all_active_for_event(event_id)

        event.deleted_at = get_current_datetime()
        await self.uow.events.update(event)
