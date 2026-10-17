import asyncio

from src.core.logger import log
from src.core.passwords import hash_password, verify_password
from src.core.tokens import create_access_token
from src.core.uow import UnitOfWork
from src.models.roles import RoleName
from src.schemas.auth import LoginRequest, RegisterRequest, RegisterResponse
from src.schemas.exceptions.domain import InvalidCredentialsError
from src.schemas.users import CreateUserSchema
from src.services.users import UserService


class AuthService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.user_service = UserService(uow=uow)

    async def _register(
        self,
        data: RegisterRequest,
        role: RoleName,
    ) -> RegisterResponse:
        password_hash = await asyncio.to_thread(
            hash_password,
            data.password,
        )

        user = await self.user_service.create_user(
            CreateUserSchema(
                email=str(data.email),
                first_name=data.first_name,
                second_name=data.second_name,
                password_hash=password_hash,
                role=role,
            )
        )

        log.info(
            "User id=%d registered with role=%s",
            user.id, role,
        )

        return RegisterResponse(**user.model_dump())

    async def register(
        self,
        data: RegisterRequest,
    ) -> RegisterResponse:
        return await self._register(data, RoleName.PARTICIPANT)

    async def register_organizer(
        self,
        data: RegisterRequest,
        created_by_id: int,
    ) -> RegisterResponse:
        user = await self._register(data, RoleName.ORGANIZER)

        log.info("Organizer id=%d registered by organizer id=%d", user.id, created_by_id)
        return user

    async def login(
        self,
        data: LoginRequest,
    ) -> str:
        user = await self.uow.users.get_by_email(
            str(data.email)
        )

        if user is None:
            log.warning("Authentication failed")
            raise InvalidCredentialsError(
                "Invalid email or password"
            )

        password_matches = await asyncio.to_thread(
            verify_password,
            data.password,
            user.password_hash,
        )

        if not password_matches:
            log.warning("Authentication failed")
            raise InvalidCredentialsError(
                "Invalid email or password"
            )

        access_token = create_access_token(
            user.id
        )

        log.info(
            "User id=%d authenticated",
            user.id,
        )

        return access_token