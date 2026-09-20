import pytest

from src.schemas.exceptions.domain import ConflictError, NotFoundError
from src.services.users import UserService


async def test_create_user(user_service: UserService):
    user = await user_service.create_user(
        email="user@example.com",
        first_name="Test",
        second_name="User",
    )

    assert user.id is not None
    assert user.email == "user@example.com"
    assert user.first_name == "Test"
    assert user.second_name == "User"
    assert user.full_name == "Test User"
    assert user.role == "participant"


async def test_create_user_with_duplicate_email_raises_conflict(
    user_service: UserService,
):
    await user_service.create_user(
        email="user@example.com",
        first_name="First",
        second_name="User",
    )

    with pytest.raises(ConflictError):
        await user_service.create_user(
            email="user@example.com",
            first_name="Second",
            second_name="User",
        )


async def test_get_user_returns_existing_user(
    user_service: UserService,
):
    created = await user_service.create_user(
        email="user@example.com",
        first_name="Test",
        second_name="User",
    )

    fetched = await user_service.get_user(created.id)

    assert fetched.id == created.id
    assert fetched.email == created.email
    assert fetched.full_name == "Test User"


async def test_get_user_raises_not_found_for_missing_user(
    user_service: UserService,
):
    with pytest.raises(NotFoundError):
        await user_service.get_user(999_999)


async def test_update_user(
    user_service: UserService,
):
    user = await user_service.create_user(
        email="user@example.com",
        first_name="Old",
        second_name="Name",
    )

    updated = await user_service.update_user(
        user.id,
        first_name="New",
        second_name="Name",
        role="organizer",
    )

    assert updated.first_name == "New"
    assert updated.second_name == "Name"
    assert updated.full_name == "New Name"
    assert updated.role == "organizer"


async def test_delete_user(
    user_service: UserService,
):
    user = await user_service.create_user(
        email="user@example.com",
        first_name="Test",
        second_name="User",
    )

    await user_service.delete_user(user.id)

    with pytest.raises(NotFoundError):
        await user_service.get_user(user.id)