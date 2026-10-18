import logging
from dataclasses import dataclass

from src.core.logger import log


@dataclass
class EventCandidate:
    event_id: int
    tag_ids: list[int]


def recommend_event_ids(
    visited_event_tag_ids: list[int],
    events: list[EventCandidate],
    limit: int,
) -> list[int]:


    visited_tags = set(visited_event_tag_ids)

    sorted_events = sorted(
        events,
        key=lambda event: len(
            visited_tags & set(event.tag_ids)
        ),
        reverse=True,
    )

    log.debug(
        "Ranking by visited tags %s: %s",
        sorted(visited_tags),
        [
            (event.event_id, len(visited_tags & set(event.tag_ids)))
            for event in sorted_events
        ],
    )

    return [
        event.event_id
        for event in sorted_events[:limit]
    ]
