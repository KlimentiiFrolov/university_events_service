from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.logger import log
from src.core.tokens import decode_access_token
from src.core.uow import UnitOfWork, get_uow
from src.models.roles import RoleName
from src.models.users import User
from src.schemas.exceptions.domain import InvalidTokenError, NotFoundError
from src.services.auth import AuthService
from src.services.events import EventService
from src.services.registrations import RegistrationService
from src.services.tags import TagService
from src.services.users import UserService

UoWDep = Annotated[UnitOfWork, Depends(get_uow)]


def get_auth_service(uow: UoWDep) -> AuthService:
    return AuthService(uow=uow)


def get_event_service(uow: UoWDep) -> EventService:
    return EventService(uow=uow)


def get_registration_service(uow: UoWDep) -> RegistrationService:
    return RegistrationService(uow=uow)


def get_user_service(uow: UoWDep) -> UserService:
    return UserService(uow=uow)


def get_tag_service(uow: UoWDep) -> TagService:
    return TagService(uow=uow)


EventServiceDep = Annotated[EventService, Depends(get_event_service)]
TagServiceDep = Annotated[TagService, Depends(get_tag_service)]
RegistrationServiceDep = Annotated[RegistrationService, Depends(get_registration_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service),]


# auto_error=False отсутствие заголовка обрабатываем сами
bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )

# TODO: пока что ходим в базу за ролью и проверкой наличия пользователя, в будущем, 
# если перейдем на access (5 минут) + refresh, то роль можно будет поместить в токен и не ходить вообще в базу, 
# т.к. вся информация будет в токене, а access живет несколько минут и потом обновляется
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    user_service: UserServiceDep,
) -> User:
    if credentials is None:
        raise _unauthorized("Not authenticated")

    try:
        user_id = decode_access_token(credentials.credentials)
        return await user_service.get_user(user_id)
    except InvalidTokenError as error:
        # Причину пишем только в лог: клиенту подробности проверки токена не нужны
        log.warning("Access token rejected: %s", error)
        raise _unauthorized("Invalid token") from error
    except NotFoundError as error:
        raise _unauthorized("User not found") from error


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: RoleName) -> Callable[..., Awaitable[User]]:
    if not roles:
        raise ValueError("require_roles() needs at least one role")

    allowed = frozenset(roles)

    async def _require_roles(user: CurrentUserDep) -> User:
        if user.role.name not in allowed:
            log.warning(
                "User id=%d with role=%s has no access, required one of: %s",
                user.id, user.role.name, ", ".join(sorted(allowed)),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

        return user

    return _require_roles


OrganizerDep = Annotated[User, Depends(require_roles(RoleName.ORGANIZER))]
ParticipantDep = Annotated[User, Depends(require_roles(RoleName.PARTICIPANT))]
AnyRoleDep = Annotated[User, Depends(require_roles(*RoleName))]
