"""Payload доменных событий: что записывается в outbox вместе с типом события."""

from pydantic import BaseModel


class RegistrationCreatedPayload(BaseModel):
    """registration.created."""

    event_id: int
    user_id: int


class RegistrationCancelledPayload(BaseModel):
    """registration.cancelled."""

    event_id: int
    user_id: int


class EventUpdatedPayload(BaseModel):
    """event.updated."""

    event_id: int
    changed_fields: list[str]


class EventCancelledPayload(BaseModel):
    """event.cancelled. Участников передаём явно: к моменту записи события их
    регистрации уже отменены, и по БД их не отличить от отменивших запись сами."""

    event_id: int
    participant_ids: list[int]
