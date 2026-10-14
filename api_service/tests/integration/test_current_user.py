"""Зависимость get_current_user: пользователь из токена в заголовке Authorization: Bearer."""

from datetime import timedelta

import jwt
import pytest
from fastapi import APIRouter, FastAPI
from httpx import AsyncClient

from dependencies import CurrentUserDep
from src.core.config import settings
from src.core.dates import get_current_datetime
from src.core.tokens import ACCESS_TOKEN_TYPE, create_access_token
from src.models.roles import RoleName
from src.models.users import User

PROBE_URL = "/probe/me"


@pytest.fixture
def test_app() -> FastAPI:
    """Приложение со служебным маршрутом, который просто отдаёт текущего пользователя."""
    router = APIRouter()

    @router.get(PROBE_URL)
    async def probe_me(user: CurrentUserDep) -> dict:
        return {"id": user.id, "email": user.email, "role": user.role.name}

    app = FastAPI()
    app.include_router(router)
    return app


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_returns_user_from_token(
    api_client: AsyncClient,
    make_user,
) -> None:
    user = await make_user(role=RoleName.ORGANIZER)

    response = await api_client.get(PROBE_URL, headers=_bearer(create_access_token(user.id)))

    assert response.status_code == 200
    assert response.json() == {"id": user.id, "email": user.email, "role": RoleName.ORGANIZER}


async def test_without_authorization_header(api_client: AsyncClient) -> None:
    response = await api_client.get(PROBE_URL)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "header",
    [
        pytest.param("Bearer", id="no-token"),
        pytest.param("Basic dXNlcjpwYXNz", id="basic-scheme"),
        pytest.param("Bearer not-a-jwt", id="malformed-token"),
    ],
)
async def test_rejects_invalid_authorization_header(
    api_client: AsyncClient,
    header: str,
) -> None:
    response = await api_client.get(PROBE_URL, headers={"Authorization": header})

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_rejects_expired_token(
    api_client: AsyncClient,
    make_user,
    caplog: pytest.LogCaptureFixture,
) -> None:
    user = await make_user()
    issued_at = get_current_datetime() - timedelta(hours=1)
    token = jwt.encode(
        {
            "sub": str(user.id),
            "type": ACCESS_TOKEN_TYPE,
            "iat": issued_at,
            "exp": issued_at + timedelta(minutes=1),
        },
        settings.auth.secret_key,
        algorithm=settings.auth.algorithm,
    )

    response = await api_client.get(PROBE_URL, headers=_bearer(token))

    assert response.status_code == 401
    # Клиенту — общее сообщение, причина — только в логе
    assert response.json()["detail"] == "Invalid token"
    assert "Access token rejected: Token has expired" in caplog.messages


async def test_rejects_token_of_unknown_user(api_client: AsyncClient) -> None:
    response = await api_client.get(PROBE_URL, headers=_bearer(create_access_token(999999)))

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_rejects_token_of_deleted_user(
    api_client: AsyncClient,
    user_service,
    make_user,
) -> None:
    user: User = await make_user()
    token = create_access_token(user.id)
    await user_service.delete_user(user.id)
    await user_service.uow.commit()

    response = await api_client.get(PROBE_URL, headers=_bearer(token))

    assert response.status_code == 401


async def test_returns_current_role_after_change(
    api_client: AsyncClient,
    user_service,
    make_user,
) -> None:
    user = await make_user(role=RoleName.PARTICIPANT)
    token = create_access_token(user.id)
    await user_service.update_user(user.id, role=RoleName.ORGANIZER)
    await user_service.uow.commit()

    response = await api_client.get(PROBE_URL, headers=_bearer(token))

    assert response.status_code == 200
    assert response.json()["role"] == RoleName.ORGANIZER
