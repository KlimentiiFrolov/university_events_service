from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from dependencies import CurrentUserIdDep, EventServiceDep
from src.models.events import Event
from src.schemas.events import (
    CreateEventSchema,
    EventFilterParams,
    EventListResponse,
    EventResponse,
    SetEventTagsSchema,
    UpdateEventSchema,
)
from src.schemas.exceptions.domain import ConflictError, ForbiddenError, NotFoundError
from src.schemas.tags import TagResponse

router = APIRouter(
    prefix="/events",
    tags=["events"],
)


# TODO: убрать после переноса преобразования сущностей в схемы в слой сервисов
def _to_event_response(event: Event) -> EventResponse:
    return EventResponse(
        id=event.id,
        title=event.title,
        text=event.text,
        location=event.location,
        event_date=event.event_date,
        capacity=event.capacity,
        created_by_id=event.created_by_id,
        created_at=event.created_at,
        tags=[
            TagResponse(id=event_tag.tag.id, name=event_tag.tag.name)
            for event_tag in event.event_tags
        ],
    )


@router.get("", response_model=EventListResponse)
async def list_events(
    service: EventServiceDep,
    filters: Annotated[EventFilterParams, Query()],
) -> EventListResponse:
    events = await service.list_events(**filters.model_dump())

    return EventListResponse(
        page=filters.page,
        total=5,
        items=[_to_event_response(event) for event in events],
    )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    service: EventServiceDep,
) -> EventResponse:
    try:
        event = await service.get_event(event_id)
    except NotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return _to_event_response(event)


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: CreateEventSchema,
    service: EventServiceDep,
    user_id: CurrentUserIdDep,
) -> EventResponse:
    try:
        event = await service.create_event(user_id, data)
    except NotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return _to_event_response(event)


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    data: UpdateEventSchema,
    service: EventServiceDep,
    user_id: CurrentUserIdDep,
) -> EventResponse:
    try:
        event = await service.update_event(event_id, user_id, data)
    except NotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ForbiddenError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
    except ConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return _to_event_response(event)


@router.put("/{event_id}/tags", response_model=EventResponse)
async def set_event_tags(
    event_id: int,
    data: SetEventTagsSchema,
    service: EventServiceDep,
    user_id: CurrentUserIdDep,
) -> EventResponse:
    try:
        event = await service.set_event_tags(event_id, user_id, data.tag_ids)
    except NotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ForbiddenError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error

    return _to_event_response(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    service: EventServiceDep,
    user_id: CurrentUserIdDep,
) -> None:
    try:
        await service.delete_event(event_id, user_id)
    except NotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ForbiddenError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
