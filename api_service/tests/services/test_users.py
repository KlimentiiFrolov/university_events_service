import pytest

from src.schemas.exceptions.domain import ConflictError, NotFoundError
from src.services.users import UserService


async def test_create_user(user_service: UserService):
    user = await user_service.create_user(
        email="user@example.com",
        full_name="Test User",
    )

    assert user.id is not None
    assert user.email == "user@example.com"
    assert user.full_name == "Test User"
    assert user.role == "participant"


async def test_create_user_with_duplicate_email_raises_conflict(
    user_service: UserService,
):
    await user_service.create_user(
        email="user@example.com",
        full_name="First User",
    )

    with pytest.raises(ConflictError):
        await user_service.create_user(
            email="user@example.com",
            full_name="Second User",
        )


async def test_get_user_returns_existing_user(
    user_service: UserService,
):
    created = await user_service.create_user(
        email="user@example.com",
        full_name="Test User",
    )

    fetched = await user_service.get_user(created.id)

    assert fetched.id == created.id
    assert fetched.email == created.email


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
        full_name="Old Name",
    )

    updated = await user_service.update_user(
        user.id,
        full_name="New Name",
        role="organizer",
    )

    assert updated.full_name == "New Name"
    assert updated.role == "organizer"


async def test_delete_user(
    user_service: UserService,
):
    user = await user_service.create_user(
        email="user@example.com",
        full_name="Test User",
    )

    await user_service.delete_user(user.id)

    with pytest.raises(NotFoundError):
        await user_service.get_user(user.id)