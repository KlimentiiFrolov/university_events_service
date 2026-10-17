from httpx import AsyncClient

from src.core.tokens import create_access_token
from src.models.roles import RoleName
from src.models.users import User

REGISTER_ORGANIZER_URL = "/api/v1/auth/register/organizer"
LOGIN_URL = "/api/v1/auth/login"

ORGANIZER_PAYLOAD = {
    "email": "new-organizer@example.com",
    "password": "SecretPassword123!",
    "first_name": "Olga",
    "second_name": "Organizer",
}


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


async def test_organizer_registers_another_organizer(api_client: AsyncClient, make_user):
    organizer = await make_user(role=RoleName.ORGANIZER)

    response = await api_client.post(
        REGISTER_ORGANIZER_URL,
        json=ORGANIZER_PAYLOAD,
        headers=_auth_headers(organizer),
    )

    assert response.status_code == 201
    assert response.json()["role"] == RoleName.ORGANIZER

    login = await api_client.post(
        LOGIN_URL,
        json={"email": ORGANIZER_PAYLOAD["email"], "password": ORGANIZER_PAYLOAD["password"]},
    )
    assert login.status_code == 200


async def test_register_organizer_requires_authentication(api_client: AsyncClient):
    response = await api_client.post(REGISTER_ORGANIZER_URL, json=ORGANIZER_PAYLOAD)

    assert response.status_code == 401


async def test_participant_cannot_register_organizer(api_client: AsyncClient, make_user):
    participant = await make_user(role=RoleName.PARTICIPANT)

    response = await api_client.post(
        REGISTER_ORGANIZER_URL,
        json=ORGANIZER_PAYLOAD,
        headers=_auth_headers(participant),
    )

    assert response.status_code == 403


async def test_register_organizer_duplicate_email_returns_conflict(
    api_client: AsyncClient,
    make_user,
):
    organizer = await make_user(role=RoleName.ORGANIZER)
    headers = _auth_headers(organizer)

    await api_client.post(REGISTER_ORGANIZER_URL, json=ORGANIZER_PAYLOAD, headers=headers)
    response = await api_client.post(
        REGISTER_ORGANIZER_URL,
        json=ORGANIZER_PAYLOAD,
        headers=headers,
    )

    assert response.status_code == 409
