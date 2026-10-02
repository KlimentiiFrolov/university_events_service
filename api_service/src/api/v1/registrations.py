from fastapi import APIRouter, HTTPException, status

from dependencies import (
    ParticipantDep,
    RegistrationServiceDep,
)
from src.models.registrations import Registration
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


def _to_registration_response(
    registration: Registration,
) -> RegistrationResponse:
    return RegistrationResponse(
        id=registration.id,
        user_id=registration.user_id,
        event_id=registration.event_id,
        status=registration.status,
        registered_at=registration.registered_at,
        cancelled_at=registration.cancelled_at,
    )


@router.get("/my", response_model=RegistrationListResponse,)
async def get_my_registrations(
    service: RegistrationServiceDep,
    participant: ParticipantDep,
) -> RegistrationListResponse:
    registrations = await service.get_my_registrations(
        participant.id
    )

    items = [
        _to_registration_response(registration)
        for registration in registrations
    ]

    return RegistrationListResponse(
        total=len(items),
        items=items,
    )


@router.post( "/{event_id}", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED,)
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

    return _to_registration_response(
        registration
    )


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

    return _to_registration_response(
        registration
    )


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

    return _to_registration_response(
        registration
    )