from typing import Annotated

from fastapi import Depends

from src.core.uow import UnitOfWork, get_uow
from src.services.events import EventService
from src.services.registrations import RegistrationService
from src.services.users import UserService
from src.services.auth import AuthService

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