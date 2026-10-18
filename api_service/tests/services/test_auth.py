import jwt
import pytest

from src.core.config import settings
from src.core.passwords import verify_password
from src.core.uow import UnitOfWork
from src.models.roles import RoleName
from src.schemas.auth import LoginRequest, RegisterRequest
from src.schemas.exceptions.domain import (
    ConflictError,
    InvalidCredentialsError,
)
from src.services.auth import AuthService


async def test_register_creates_participant_with_hashed_password(
    uow: UnitOfWork,
):
    service = AuthService(uow)

    data = RegisterRequest(
        email="participant@example.com",
        password="SecretPassword123!",
        first_name="Ivan",
        second_name="Ivanov",
    )

    user = await service.register(data)

    assert user.id is not None
    assert user.email == data.email
    assert user.role == RoleName.PARTICIPANT

    persisted = await uow.users.get_by_id(user.id)

    assert persisted is not None
    assert persisted.password_hash != data.password
    assert verify_password(
        data.password,
        persisted.password_hash,
    )


async def test_register_duplicate_email_raises_conflict(
    uow: UnitOfWork,
):
    service = AuthService(uow)

    data = RegisterRequest(
        email="participant@example.com",
        password="SecretPassword123!",
        first_name="Ivan",
        second_name="Ivanov",
    )

    await service.register(data)

    with pytest.raises(ConflictError):
        await service.register(data)


async def test_login_returns_valid_access_token(
    uow: UnitOfWork,
):
    service = AuthService(uow)

    register_data = RegisterRequest(
        email="participant@example.com",
        password="SecretPassword123!",
        first_name="Ivan",
        second_name="Ivanov",
    )

    user = await service.register(register_data)

    access_token = await service.login(
        LoginRequest(
            email="participant@example.com",
            password="SecretPassword123!",
        )
    )

    payload = jwt.decode(
        access_token,
        settings.auth.secret_key,
        algorithms=[settings.auth.algorithm],
    )

    assert payload["sub"] == str(user.id)
    assert payload["type"] == "access"
    assert "iat" in payload
    assert "exp" in payload


async def test_login_with_wrong_password_fails(
    uow: UnitOfWork,
):
    service = AuthService(uow)

    await service.register(
        RegisterRequest(
            email="participant@example.com",
            password="SecretPassword123!",
            first_name="Ivan",
            second_name="Ivanov",
        )
    )

    with pytest.raises(InvalidCredentialsError):
        await service.login(
            LoginRequest(
                email="participant@example.com",
                password="WrongPassword123!",
            )
        )


async def test_login_with_unknown_email_fails(
    uow: UnitOfWork,
):
    service = AuthService(uow)

    with pytest.raises(InvalidCredentialsError):
        await service.login(
            LoginRequest(
                email="unknown@example.com",
                password="SecretPassword123!",
            )
        )


def _organizer_data() -> RegisterRequest:
    return RegisterRequest(
        email="organizer@example.com",
        password="SecretPassword123!",
        first_name="Olga",
        second_name="Organizer",
    )


async def test_register_organizer_creates_organizer(
    uow: UnitOfWork,
    make_user,
):
    creator = await make_user(role=RoleName.ORGANIZER)
    service = AuthService(uow)

    user = await service.register_organizer(_organizer_data(), creator.id)

    assert user.role == RoleName.ORGANIZER

    persisted = await uow.users.get_by_id(user.id)

    assert persisted is not None
    assert persisted.role.name == RoleName.ORGANIZER


async def test_register_organizer_duplicate_email_raises_conflict(
    uow: UnitOfWork,
    make_user,
):
    creator = await make_user(role=RoleName.ORGANIZER)
    service = AuthService(uow)

    await service.register(_organizer_data())

    with pytest.raises(ConflictError):
        await service.register_organizer(_organizer_data(), creator.id)
