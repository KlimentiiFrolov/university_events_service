"""Проверки самой обвязки интеграционных тестов на существующем роутере auth."""

from httpx import AsyncClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"

CREDENTIALS = {
    "email": "smoke@example.com",
    "password": "SmokePassword123!",
}
REGISTER_BODY = {
    **CREDENTIALS,
    "first_name": "Smoke",
    "second_name": "Test",
}


async def test_data_persists_between_requests(api_client: AsyncClient) -> None:
    register = await api_client.post(REGISTER_URL, json=REGISTER_BODY)
    assert register.status_code == 201

    login = await api_client.post(LOGIN_URL, json=CREDENTIALS)
    assert login.status_code == 200
    assert login.json()["access_token"]


async def test_failed_request_does_not_roll_back_test_data(api_client: AsyncClient) -> None:
    assert (await api_client.post(REGISTER_URL, json=REGISTER_BODY)).status_code == 201

    duplicate = await api_client.post(REGISTER_URL, json=REGISTER_BODY)
    assert duplicate.status_code == 409

    login = await api_client.post(LOGIN_URL, json=CREDENTIALS)
    assert login.status_code == 200


async def test_data_is_isolated_between_tests(api_client: AsyncClient) -> None:
    # Пользователь из предыдущих тестов откатился вместе с их транзакцией
    login = await api_client.post(LOGIN_URL, json=CREDENTIALS)
    assert login.status_code == 401
