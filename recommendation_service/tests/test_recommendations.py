from src.services.recommendations import (
    EventCandidate,
    recommend_event_ids,
)


def test_recommendations():
    events = [
        EventCandidate(10, [1, 2]),
        EventCandidate(11, [3]),
        EventCandidate(12, [4, 5]),
        EventCandidate(13, [1, 2, 3]),
    ]

    result = recommend_event_ids(
        visited_event_tag_ids=[1, 2, 3],
        events=events,
        limit=4,
    )

    assert result == [13, 10, 11, 12]


def test_empty_history():
    events = [
        EventCandidate(10, [1]),
        EventCandidate(20, [2]),
    ]

    result = recommend_event_ids(
        visited_event_tag_ids=[],
        events=events,
        limit=2,
    )

    assert result == [10, 20]
