from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.tokens import create_access_token
from src.events.types import DomainEventType
from src.models.outbox import OutboxMessage
from src.models.roles import RoleName
from src.models.users import User

REGISTRATIONS_URL = "/api/v1/registrations"
EVENTS_URL = "/api/v1/events"


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


async def _outbox(session_maker: async_sessionmaker[AsyncSession]) -> list[OutboxMessage]:
    async with session_maker() as session:
        result = await session.scalars(
            select(OutboxMessage).order_by(OutboxMessage.created_at)
        )
        return list(result.all())


async def test_register_writes_registration_created(
    api_client: AsyncClient,
    session_maker,
    make_user,
    make_event,
):
    participant = await make_user(role=RoleName.PARTICIPANT)
    event = await make_event()

    response = await api_client.post(
        f"{REGISTRATIONS_URL}/{event.id}",
        headers=_auth_headers(participant),
    )

    assert response.status_code == 201
    messages = await _outbox(session_maker)
    assert len(messages) == 1
    message = messages[0]
    assert message.routing_key == DomainEventType.REGISTRATION_CREATED
    assert message.payload == {"event_id": event.id, "user_id": participant.id}


async def test_failed_register_writes_nothing(
    api_client: AsyncClient,
    session_maker,
    make_user,
    make_event,
):
    participant = await make_user(role=RoleName.PARTICIPANT)
    event = await make_event()
    headers = _auth_headers(participant)
    await api_client.post(f"{REGISTRATIONS_URL}/{event.id}", headers=headers)

    response = await api_client.post(f"{REGISTRATIONS_URL}/{event.id}", headers=headers)

    assert response.status_code == 409
    messages = await _outbox(session_maker)
    assert [message.routing_key for message in messages] == [
        DomainEventType.REGISTRATION_CREATED,
    ]


async def test_cancel_and_reregister_write_events(
    api_client: AsyncClient,
    session_maker,
    make_user,
    make_event,
):
    participant = await make_user(role=RoleName.PARTICIPANT)
    event = await make_event()
    headers = _auth_headers(participant)
    await api_client.post(f"{REGISTRATIONS_URL}/{event.id}", headers=headers)

    cancel = await api_client.delete(f"{REGISTRATIONS_URL}/{event.id}", headers=headers)
    reregister = await api_client.post(
        f"{REGISTRATIONS_URL}/{event.id}/reregister",
        headers=headers,
    )

    assert cancel.status_code == 200
    assert reregister.status_code == 200
    messages = await _outbox(session_maker)
    assert [message.routing_key for message in messages] == [
        DomainEventType.REGISTRATION_CREATED,
        DomainEventType.REGISTRATION_CANCELLED,
        DomainEventType.REGISTRATION_CREATED,
    ]


async def test_update_event_writes_changed_fields(
    api_client: AsyncClient,
    session_maker,
    make_user,
    make_event,
):
    organizer = await make_user(role=RoleName.ORGANIZER)
    event = await make_event(created_by_id=organizer.id)

    response = await api_client.patch(
        f"{EVENTS_URL}/{event.id}",
        json={"location": "Room 101"},
        headers=_auth_headers(organizer),
    )

    assert response.status_code == 200
    messages = await _outbox(session_maker)
    assert len(messages) == 1
    message = messages[0]
    assert message.routing_key == DomainEventType.EVENT_UPDATED
    assert message.payload == {"event_id": event.id, "changed_fields": ["location"]}


async def test_update_event_without_changes_writes_nothing(
    api_client: AsyncClient,
    session_maker,
    make_user,
    make_event,
):
    organizer = await make_user(role=RoleName.ORGANIZER)
    event = await make_event(created_by_id=organizer.id)

    response = await api_client.patch(
        f"{EVENTS_URL}/{event.id}",
        json={},
        headers=_auth_headers(organizer),
    )

    assert response.status_code == 200
    assert await _outbox(session_maker) == []


async def test_forbidden_update_writes_nothing(
    api_client: AsyncClient,
    session_maker,
    make_user,
    make_event,
):
    stranger = await make_user(role=RoleName.ORGANIZER)
    event = await make_event()

    response = await api_client.patch(
        f"{EVENTS_URL}/{event.id}",
        json={"location": "Room 101"},
        headers=_auth_headers(stranger),
    )

    assert response.status_code == 403
    assert await _outbox(session_maker) == []


async def test_delete_event_writes_cancelled_participants(
    api_client: AsyncClient,
    session_maker,
    make_user,
    make_event,
):
    organizer = await make_user(role=RoleName.ORGANIZER)
    participant = await make_user(role=RoleName.PARTICIPANT)
    event = await make_event(created_by_id=organizer.id)
    await api_client.post(
        f"{REGISTRATIONS_URL}/{event.id}",
        headers=_auth_headers(participant),
    )

    response = await api_client.delete(
        f"{EVENTS_URL}/{event.id}",
        headers=_auth_headers(organizer),
    )

    assert response.status_code == 204
    messages = await _outbox(session_maker)
    assert [message.routing_key for message in messages] == [
        DomainEventType.REGISTRATION_CREATED,
        DomainEventType.EVENT_CANCELLED,
    ]
    assert messages[1].payload == {"event_id": event.id, "participant_ids": [participant.id]}
