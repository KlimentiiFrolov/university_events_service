"""Зависимость require_roles(*roles): доступ к эндпоинту только для перечисленных ролей."""

import pytest
from fastapi import APIRouter, FastAPI
from httpx import AsyncClient

from dependencies import AnyRoleDep, OrganizerDep, ParticipantDep, require_roles
from src.core.tokens import create_access_token
from src.models.roles import RoleName
from src.models.users import User

ORGANIZER_ONLY_URL = "/probe/organizer-only"
PARTICIPANT_ONLY_URL = "/probe/participant-only"
ANY_ROLE_URL = "/probe/any-role"


@pytest.fixture
def test_app() -> FastAPI:
    """Приложение со служебными маршрутами под разные наборы ролей."""
    router = APIRouter()

    @router.get(ORGANIZER_ONLY_URL)
    async def organizer_only(user: OrganizerDep) -> dict:
        return {"id": user.id}

    @router.get(PARTICIPANT_ONLY_URL)
    async def participant_only(user: ParticipantDep) -> dict:
        return {"id": user.id}

    @router.get(ANY_ROLE_URL)
    async def any_role(user: AnyRoleDep) -> dict:
        return {"id": user.id}

    app = FastAPI()
    app.include_router(router)
    return app


def _bearer(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.mark.parametrize(
    "url,allowed_roles",
    [
        pytest.param(ORGANIZER_ONLY_URL, {RoleName.ORGANIZER}, id="organizer-only"),
        pytest.param(PARTICIPANT_ONLY_URL, {RoleName.PARTICIPANT}, id="participant-only"),
        pytest.param(ANY_ROLE_URL, set(RoleName), id="any-role"),
    ],
)
@pytest.mark.parametrize("role", list(RoleName))
async def test_access_depends_on_role(
    api_client: AsyncClient,
    make_user,
    url: str,
    allowed_roles: set[RoleName],
    role: RoleName,
) -> None:
    user = await make_user(role=role)

    response = await api_client.get(url, headers=_bearer(user))

    if role in allowed_roles:
        assert response.status_code == 200
        assert response.json() == {"id": user.id}
    else:
        assert response.status_code == 403
        assert response.json()["detail"] == "Not enough permissions"


async def test_forbidden_access_is_logged(
    api_client: AsyncClient,
    make_user,
    caplog: pytest.LogCaptureFixture,
) -> None:
    participant = await make_user(role=RoleName.PARTICIPANT)

    await api_client.get(ORGANIZER_ONLY_URL, headers=_bearer(participant))

    assert any(f"User id={participant.id}" in message for message in caplog.messages)


@pytest.mark.parametrize("url", [ORGANIZER_ONLY_URL, PARTICIPANT_ONLY_URL, ANY_ROLE_URL])
async def test_requires_authentication_before_role_check(
    api_client: AsyncClient,
    url: str,
) -> None:
    response = await api_client.get(url)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_uses_current_role_from_database(
    api_client: AsyncClient,
    user_service,
    make_user,
) -> None:
    organizer = await make_user(role=RoleName.ORGANIZER)
    headers = _bearer(organizer)
    await user_service.update_user(organizer.id, role=RoleName.PARTICIPANT)
    await user_service.uow.commit()

    # Токен выдан, когда пользователь был организатором, но роль уже сменилась
    assert (await api_client.get(ORGANIZER_ONLY_URL, headers=headers)).status_code == 403
    assert (await api_client.get(PARTICIPANT_ONLY_URL, headers=headers)).status_code == 200


def test_require_roles_without_roles_is_an_error() -> None:
    with pytest.raises(ValueError):
        require_roles()
