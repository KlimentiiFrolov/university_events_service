import pytest

from src.core.passwords import hash_password
from src.schemas.exceptions.domain import ConflictError, NotFoundError
from src.schemas.users import CreateUserSchema
from src.services.users import UserService

PASSWORD_HASH = hash_password("TestPassword123!")

async def test_create_user(user_service: UserService):
    data = CreateUserSchema(
        email="user@example.com",
        first_name="Test",
        second_name="User",
        password_hash=PASSWORD_HASH,
    )

    user = await user_service.create_user(data)

    assert user.id is not None
    assert user.email == data.email
    assert user.first_name == data.first_name
    assert user.second_name == data.second_name
    assert user.role == data.role

    persisted = await user_service.uow.users.get_by_id(user.id)
    assert persisted is not None
    assert persisted.password_hash == data.password_hash


async def test_create_user_with_duplicate_email_raises_conflict(
    user_service: UserService,
):
    await user_service.create_user(
        CreateUserSchema(
        email="user@example.com",
        first_name="First",
        second_name="User",
        password_hash=PASSWORD_HASH,
    ))

    with pytest.raises(ConflictError):
        await user_service.create_user(
            CreateUserSchema(
            email="user@example.com",
            first_name="Second",
            second_name="User",
            password_hash=PASSWORD_HASH,
        ))


async def test_get_user_returns_existing_user(
    user_service: UserService,
):
    created = await user_service.create_user(
        CreateUserSchema(
        email="user@example.com",
        first_name="Test",
        second_name="User",
        password_hash=PASSWORD_HASH,
    ))

    fetched = await user_service.get_user(created.id)

    assert fetched == created


async def test_get_user_raises_not_found_for_missing_user(
    user_service: UserService,
):
    with pytest.raises(NotFoundError):
        await user_service.get_user(999_999)


async def test_update_user(
    user_service: UserService,
):
    user = await user_service.create_user(
        CreateUserSchema(
        email="user@example.com",
        first_name="Old",
        second_name="Name",
        password_hash=PASSWORD_HASH,
    ))

    new_first_name = "New"
    new_second_name = "Surname"

    updated = await user_service.update_user(
        user.id,
        first_name=new_first_name,
        second_name=new_second_name,
    )

    assert updated.first_name == new_first_name
    assert updated.second_name == new_second_name


async def test_delete_user(
    user_service: UserService,
):
    user = await user_service.create_user(
        CreateUserSchema(
        email="user@example.com",
        first_name="Test",
        second_name="User",
        password_hash=PASSWORD_HASH,
    ))

    await user_service.delete_user(user.id)

    with pytest.raises(NotFoundError):
        await user_service.get_user(user.id)