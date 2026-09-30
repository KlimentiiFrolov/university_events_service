from sqlalchemy.exc import IntegrityError

from src.core.logger import log
from src.core.uow import UnitOfWork
from src.models.roles import Role, RoleName
from src.models.users import User
from src.schemas.exceptions.domain import (
    ConflictError,
    NotFoundError,
)
from src.schemas.users import CreateUserSchema


class UserService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def _get_role_by_name(self, name: RoleName) -> Role:
        role = await self.uow.roles.get_by_name(name)

        if role is None:
            log.warning("Role name=%s not found", name.value)
            raise NotFoundError("Role", name.value)

        log.debug("Role name=%s found", name.value)
        return role

    async def create_user(
            self,
            data: CreateUserSchema,
    ) -> User:
        existing = await self.uow.users.get_by_email(
            data.email
        )

        if existing is not None:
            log.warning(
                "User with this email already exists "
                "(id=%d)",
                existing.id,
            )
            raise ConflictError(
                f"User with email={data.email} "
                "already exists"
            )

        role_entity = await self._get_role_by_name(
            data.role
        )

        user = User(
            email=data.email,
            first_name=data.first_name,
            second_name=data.second_name,
            password_hash=data.password_hash,
            role=role_entity,
        )

        try:
            user = await self.uow.users.add(user)
        except IntegrityError as error:
            log.warning(
                "User with this email already "
                "exists (concurrent insert)"
            )
            raise ConflictError(
                f"User with email={data.email} "
                "already exists"
            ) from error

        log.info(
            "User id=%d created with role=%s",
            user.id,
            data.role.value,
        )

        return user

    async def get_user(
        self,
        user_id: int,
    ) -> User:
        user = await self.uow.users.get_by_id(user_id)

        if user is None:
            log.warning("User id=%d not found", user_id)
            raise NotFoundError(
                "User",
                user_id,
            )

        log.debug("User id=%d found", user_id)
        return user

    async def get_users(self) -> list[User]:
        users = await self.uow.users.get_all()

        log.debug("Listed %d users", len(users))
        return users

    async def update_user(
        self,
        user_id: int,
        *,
        first_name: str | None = None,
        second_name: str | None = None,
        role: RoleName | None = None,
    ) -> User:
        user = await self.get_user(user_id)
        updated_fields = []

        if first_name is not None:
            user.first_name = first_name
            updated_fields.append("first_name")

        if second_name is not None:
            user.second_name = second_name
            updated_fields.append("second_name")

        if role is not None:
            user.role = await self._get_role_by_name(role)
            updated_fields.append("role")

        user = await self.uow.users.update(user)

        log.info("User id=%d updated, fields: %s", user_id, tuple(updated_fields))
        return user

    async def delete_user(
        self,
        user_id: int,
    ) -> None:
        user = await self.get_user(user_id)

        await self.uow.users.delete(user)

        log.info("User id=%d deleted", user_id)
