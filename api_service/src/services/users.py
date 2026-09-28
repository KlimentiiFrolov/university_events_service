from sqlalchemy.exc import IntegrityError

from src.core.uow import UnitOfWork
from src.models.roles import Role, RoleName
from src.models.users import User
from src.schemas.exceptions.domain import (
    ConflictError,
    NotFoundError,
)


class UserService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def _get_role_by_name(self, name: RoleName) -> Role:
        role = await self.uow.roles.get_by_name(name)

        if role is None:
            raise NotFoundError("Role", name.value)

        return role

    async def create_user(
        self,
        email: str,
        first_name: str,
        second_name: str,
        role: RoleName = RoleName.PARTICIPANT,
    ) -> User:
        existing = await self.uow.users.get_by_email(email)

        if existing is not None:
            raise ConflictError(
                f"User with email={email} already exists"
            )

        role_entity = await self._get_role_by_name(role)

        user = User(
            email=email,
            first_name=first_name,
            second_name=second_name,
            role=role_entity,
        )

        try:
            return await self.uow.users.add(user)
        except IntegrityError as error:
            raise ConflictError(
                f"User with email={email} already exists"
            ) from error

    async def get_user(
        self,
        user_id: int,
    ) -> User:
        user = await self.uow.users.get_by_id(user_id)

        if user is None:
            raise NotFoundError(
                "User",
                user_id,
            )

        return user

    async def get_users(self) -> list[User]:
        return await self.uow.users.get_all()

    async def update_user(
        self,
        user_id: int,
        *,
        first_name: str | None = None,
        second_name: str | None = None,
        role: RoleName | None = None,
    ) -> User:
        user = await self.get_user(user_id)

        if first_name is not None:
            user.first_name = first_name

        if second_name is not None:
            user.second_name = second_name

        if role is not None:
            user.role = await self._get_role_by_name(role)

        return await self.uow.users.update(user)

    async def delete_user(
        self,
        user_id: int,
    ) -> None:
        user = await self.get_user(user_id)

        await self.uow.users.delete(user)