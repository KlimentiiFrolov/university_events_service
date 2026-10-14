from dataclasses import dataclass


@dataclass
class EventCandidate:
    event_id: int
    tag_ids: list[int]


def recommend_event_ids(
    visited_event_tag_ids: list[int],
    events: list[EventCandidate],
    limit: int,
) -> list[int]:

    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    visited_tags = set(visited_event_tag_ids)

    sorted_events = sorted(
        events,
        key=lambda event: len(
            visited_tags & set(event.tag_ids)
        ),
        reverse=True,
    )

    # Возвращаем только ID
    return [
        event.event_id
        for event in sorted_events[:limit]
    ]
