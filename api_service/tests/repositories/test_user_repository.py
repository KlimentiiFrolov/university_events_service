import pytest
from sqlalchemy.exc import IntegrityError

from src.core.uow import UnitOfWork
from src.models.users import User


async def test_add_persists_user_and_assigns_id(
    make_user,
):
    user = await make_user(
        email="user@example.com",
        first_name="Test",
        second_name="User",
    )

    assert user.id is not None
    assert user.email == "user@example.com"
    assert user.first_name == "Test"
    assert user.second_name == "User"
    assert user.full_name == "Test User"


async def test_get_by_id_returns_existing_user(
    uow: UnitOfWork,
    make_user,
):
    user = await make_user()

    fetched = await uow.users.get_by_id(user.id)

    assert fetched is not None
    assert fetched.id == user.id


async def test_get_by_id_returns_none_for_missing_user(
    uow: UnitOfWork,
):
    fetched = await uow.users.get_by_id(999_999)

    assert fetched is None


async def test_get_by_email_returns_existing_user(
    uow: UnitOfWork,
    make_user,
):
    await make_user(
        email="user@example.com",
    )

    fetched = await uow.users.get_by_email(
        "user@example.com"
    )

    assert fetched is not None
    assert fetched.email == "user@example.com"


async def test_get_by_email_returns_none_for_missing_user(
    uow: UnitOfWork,
):
    fetched = await uow.users.get_by_email(
        "missing@example.com"
    )

    assert fetched is None


async def test_get_all_returns_users(
    uow: UnitOfWork,
    make_user,
):
    first = await make_user()
    second = await make_user()

    users = await uow.users.get_all()

    assert {user.id for user in users} == {
        first.id,
        second.id,
    }


async def test_update_user(
    uow: UnitOfWork,
    make_user,
):
    user = await make_user(
        first_name="Old",
        second_name="Name",
    )

    user.first_name = "New"

    updated = await uow.users.update(user)

    assert updated.first_name == "New"
    assert updated.full_name == "New Name"


async def test_delete_user(
    uow: UnitOfWork,
    make_user,
):
    user = await make_user()

    await uow.users.delete(user)

    fetched = await uow.users.get_by_id(user.id)

    assert fetched is None


async def test_duplicate_email_raises_integrity_error(
    uow: UnitOfWork,
    make_user,
):
    await make_user(
        email="same@example.com",
    )

    duplicate = User(
        email="same@example.com",
        first_name="Another",
        second_name="User",
        role="participant",
    )

    with pytest.raises(IntegrityError):
        await uow.users.add(duplicate)

    await uow.rollback()