from src.models.events import Event
from src.schemas.events import EventResponse
from src.schemas.tags import TagResponse


def to_event_response(event: Event) -> EventResponse:
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
            TagResponse.model_validate(event_tag.tag)
            for event_tag in event.event_tags
        ],
    )
