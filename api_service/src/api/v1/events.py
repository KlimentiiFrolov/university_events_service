from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from dependencies import EventServiceDep
from src.models.events import Event
from src.schemas.events import EventFilterParams, EventListResponse, EventResponse
from src.schemas.exceptions.domain import NotFoundError
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
    filters: EventFilterParams,
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
