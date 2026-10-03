from httpx import AsyncClient

from src.core.tokens import create_access_token
from src.models.registrations import RegistrationStatus
from src.models.roles import RoleName
from src.models.users import User

REGISTRATIONS_URL = "/api/v1/registrations"
EVENTS_URL = "/api/v1/events"


def _auth_headers(
    user: User,
) -> dict[str, str]:
    return {
        "Authorization": (
            f"Bearer {create_access_token(user.id)}"
        )
    }


async def test_register_for_event(
    api_client: AsyncClient,
    make_user,
    make_event,
):
    participant = await make_user(
        role=RoleName.PARTICIPANT
    )
    event = await make_event()

    response = await api_client.post(
        f"{REGISTRATIONS_URL}/{event.id}",
        headers=_auth_headers(participant),
    )

    assert response.status_code == 201

    body = response.json()

    assert body["user_id"] == participant.id
    assert body["event_id"] == event.id
    assert body["status"] == RegistrationStatus.ACTIVE
    assert body["cancelled_at"] is None


async def test_register_requires_auth(
    api_client: AsyncClient,
    make_event,
):
    event = await make_event()

    response = await api_client.post(
        f"{REGISTRATIONS_URL}/{event.id}"
    )

    assert response.status_code == 401


async def test_register_forbids_organizer(
    api_client: AsyncClient,
    make_user,
    make_event,
):
    organizer = await make_user(
        role=RoleName.ORGANIZER
    )
    event = await make_event()

    response = await api_client.post(
        f"{REGISTRATIONS_URL}/{event.id}",
        headers=_auth_headers(organizer),
    )

    assert response.status_code == 403


async def test_register_duplicate_returns_conflict(
    api_client: AsyncClient,
    make_user,
    make_event,
):
    participant = await make_user()
    event = await make_event()

    url = f"{REGISTRATIONS_URL}/{event.id}"
    headers = _auth_headers(participant)

    first = await api_client.post(
        url,
        headers=headers,
    )
    second = await api_client.post(
        url,
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 409


async def test_register_missing_event_returns_not_found(
    api_client: AsyncClient,
    make_user,
):
    participant = await make_user()

    response = await api_client.post(
        f"{REGISTRATIONS_URL}/999999",
        headers=_auth_headers(participant),
    )

    assert response.status_code == 404


async def test_capacity_limit_returns_conflict(
    api_client: AsyncClient,
    make_user,
    make_event,
):
    event = await make_event(
        capacity=1
    )

    first = await make_user()
    second = await make_user()

    assert (
        await api_client.post(
            f"{REGISTRATIONS_URL}/{event.id}",
            headers=_auth_headers(first),
        )
    ).status_code == 201

    response = await api_client.post(
        f"{REGISTRATIONS_URL}/{event.id}",
        headers=_auth_headers(second),
    )

    assert response.status_code == 409


async def test_cancel_registration(
    api_client: AsyncClient,
    make_user,
    make_event,
):
    participant = await make_user()
    event = await make_event()

    url = f"{REGISTRATIONS_URL}/{event.id}"
    headers = _auth_headers(participant)

    await api_client.post(
        url,
        headers=headers,
    )

    response = await api_client.delete(
        url,
        headers=headers,
    )

    assert response.status_code == 200
    assert (
        response.json()["status"]
        == RegistrationStatus.CANCELLED
    )
    assert response.json()["cancelled_at"] is not None


async def test_cancel_twice_returns_conflict(
    api_client: AsyncClient,
    make_user,
    make_event,
):
    participant = await make_user()
    event = await make_event()

    url = f"{REGISTRATIONS_URL}/{event.id}"
    headers = _auth_headers(participant)

    await api_client.post(
        url,
        headers=headers,
    )
    await api_client.delete(
        url,
        headers=headers,
    )

    response = await api_client.delete(
        url,
        headers=headers,
    )

    assert response.status_code == 409


async def test_reregister_cancelled_registration(
    api_client: AsyncClient,
    make_user,
    make_event,
):
    participant = await make_user()
    event = await make_event()

    url = f"{REGISTRATIONS_URL}/{event.id}"
    headers = _auth_headers(participant)

    await api_client.post(
        url,
        headers=headers,
    )
    await api_client.delete(
        url,
        headers=headers,
    )

    response = await api_client.post(
        f"{url}/reregister",
        headers=headers,
    )

    assert response.status_code == 200
    assert (
        response.json()["status"]
        == RegistrationStatus.ACTIVE
    )
    assert response.json()["cancelled_at"] is None


async def test_reregister_active_returns_conflict(
    api_client: AsyncClient,
    make_user,
    make_event,
):
    participant = await make_user()
    event = await make_event()

    url = f"{REGISTRATIONS_URL}/{event.id}"
    headers = _auth_headers(participant)

    await api_client.post(
        url,
        headers=headers,
    )

    response = await api_client.post(
        f"{url}/reregister",
        headers=headers,
    )

    assert response.status_code == 409


async def test_get_my_registrations(
    api_client: AsyncClient,
    make_user,
    make_event,
):
    participant = await make_user()
    other_participant = await make_user()

    first_event = await make_event()
    second_event = await make_event()

    headers = _auth_headers(participant)

    await api_client.post(
        f"{REGISTRATIONS_URL}/{first_event.id}",
        headers=headers,
    )
    await api_client.post(
        f"{REGISTRATIONS_URL}/{second_event.id}",
        headers=headers,
    )

    await api_client.post(
        f"{REGISTRATIONS_URL}/{first_event.id}",
        headers=_auth_headers(other_participant),
    )

    response = await api_client.get(
        f"{REGISTRATIONS_URL}/my",
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 2
    assert {
        registration["event_id"]
        for registration in body["items"]
    } == {
        first_event.id,
        second_event.id,
    }


async def test_owner_can_get_active_event_participants(
    api_client: AsyncClient,
    make_user,
    make_event,
):
    organizer = await make_user(
        role=RoleName.ORGANIZER
    )
    first_participant = await make_user()
    second_participant = await make_user()

    event = await make_event(
        created_by_id=organizer.id
    )

    first_headers = _auth_headers(
        first_participant
    )
    second_headers = _auth_headers(
        second_participant
    )

    registration_url = (
        f"{REGISTRATIONS_URL}/{event.id}"
    )

    await api_client.post(
        registration_url,
        headers=first_headers,
    )
    await api_client.post(
        registration_url,
        headers=second_headers,
    )

    await api_client.delete(
        registration_url,
        headers=second_headers,
    )

    response = await api_client.get(
        f"{EVENTS_URL}/{event.id}/participants",
        headers=_auth_headers(organizer),
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 1
    assert body["items"][0]["id"] == first_participant.id


async def test_other_organizer_cannot_get_event_participants(
    api_client: AsyncClient,
    make_user,
    make_event,
):
    owner = await make_user(
        role=RoleName.ORGANIZER
    )
    other_organizer = await make_user(
        role=RoleName.ORGANIZER
    )

    event = await make_event(
        created_by_id=owner.id
    )

    response = await api_client.get(
        f"{EVENTS_URL}/{event.id}/participants",
        headers=_auth_headers(other_organizer),
    )

    assert response.status_code == 403


async def test_participant_cannot_get_event_participants(
    api_client: AsyncClient,
    make_user,
    make_event,
):
    participant = await make_user()
    event = await make_event()

    response = await api_client.get(
        f"{EVENTS_URL}/{event.id}/participants",
        headers=_auth_headers(participant),
    )

    assert response.status_code == 403