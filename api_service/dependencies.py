from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from src.core.uow import UnitOfWork, get_uow
from src.services.auth import AuthService
from src.services.events import EventService
from src.services.registrations import RegistrationService
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


EventServiceDep = Annotated[EventService, Depends(get_event_service)]
RegistrationServiceDep = Annotated[RegistrationService, Depends(get_registration_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service),]


# TODO: временная заглушка до зависимости авторизации по JWT (require_roles(*roles))
def get_current_user_id(
    x_user_id: Annotated[int | None, Header()] = None,
) -> int:
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    return x_user_id


CurrentUserIdDep = Annotated[int, Depends(get_current_user_id)]