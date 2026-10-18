from fastapi import APIRouter, HTTPException, status

from dependencies import (
    ParticipantDep,
    RegistrationServiceDep,
)
from src.schemas.exceptions.domain import (
    ConflictError,
    NotFoundError,
)
from src.schemas.registrations import (
    RegistrationListResponse,
    RegistrationResponse,
)

router = APIRouter(
    prefix="/registrations",
    tags=["registrations"],
)


@router.get("/my", response_model=RegistrationListResponse,)
async def get_my_registrations(
    service: RegistrationServiceDep,
    participant: ParticipantDep,
) -> RegistrationListResponse:
    registrations = await service.get_my_registrations(
        participant.id
    )

    return RegistrationListResponse(
        total=len(registrations),
        items=registrations,
    )


@router.post("/{event_id}", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED,)
async def register_for_event(
    event_id: int,
    service: RegistrationServiceDep,
    participant: ParticipantDep,
) -> RegistrationResponse:
    try:
        registration = await service.register(
            participant.id,
            event_id,
        )
    except NotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return registration


@router.delete("/{event_id}", response_model=RegistrationResponse,)
async def cancel_registration(
    event_id: int,
    service: RegistrationServiceDep,
    participant: ParticipantDep,
) -> RegistrationResponse:
    try:
        registration = await service.cancel(
            participant.id,
            event_id,
        )
    except NotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return registration


@router.post("/{event_id}/reregister", response_model=RegistrationResponse,)
async def reregister_for_event(
    event_id: int,
    service: RegistrationServiceDep,
    participant: ParticipantDep,
) -> RegistrationResponse:
    try:
        registration = await service.reregister(
            participant.id,
            event_id,
        )
    except NotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return registration