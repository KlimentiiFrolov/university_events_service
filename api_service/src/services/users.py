from sqlalchemy.exc import IntegrityError

from src.models.users import User
from src.repositories.users import UserRepository
from src.schemas.exceptions.domain import (
    ConflictError,
    NotFoundError,
)


class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def create_user(
        self,
        email: str,
        full_name: str,
        role: str = "participant",
    ) -> User:
        existing = await self.repository.get_by_email(email)

        if existing is not None:
            raise ConflictError(
                f"User with email={email} already exists"
            )

        user = User(
            email=email,
            full_name=full_name,
            role=role,
        )

        try:
            return await self.repository.add(user)
        except IntegrityError as error:
            raise ConflictError(
                f"User with email={email} already exists"
            ) from error

    async def get_user(
        self,
        user_id: int,
    ) -> User:
        user = await self.repository.get_by_id(user_id)

        if user is None:
            raise NotFoundError(
                "User",
                user_id,
            )

        return user

    async def get_users(self) -> list[User]:
        return await self.repository.get_all()

    async def update_user(
        self,
        user_id: int,
        *,
        full_name: str | None = None,
        role: str | None = None,
    ) -> User:
        user = await self.get_user(user_id)

        if full_name is not None:
            user.full_name = full_name

        if role is not None:
            user.role = role

        return await self.repository.update(user)

    async def delete_user(
        self,
        user_id: int,
    ) -> None:
        user = await self.get_user(user_id)

        await self.repository.delete(user)