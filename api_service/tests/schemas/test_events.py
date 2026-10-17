from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.schemas.events import (
    CreateEventSchema,
    EventFilterParams,
    SetEventTagsSchema,
    UpdateEventSchema,
)

EVENT_DATA = {
    "title": "Lecture",
    "location": "Room 101",
    "event_date": datetime(2026, 1, 10, tzinfo=UTC),
    "capacity": 30,
}


@pytest.mark.parametrize(
    "tag_ids,expected",
    [
        pytest.param([3, 1, 3, 2, 1], [3, 1, 2], id="duplicates-keep-first-order"),
        pytest.param([1, 2], [1, 2], id="no-duplicates"),
        pytest.param([], [], id="empty"),
    ],
)
def test_set_event_tags_removes_duplicates(tag_ids: list[int], expected: list[int]):
    assert SetEventTagsSchema(tag_ids=tag_ids).tag_ids == expected


def test_create_event_removes_duplicate_tag_ids():
    schema = CreateEventSchema(**EVENT_DATA, tag_ids=[1, 1, 2])

    assert schema.tag_ids == [1, 2]


def test_create_event_without_tag_ids_keeps_none():
    assert CreateEventSchema(**EVENT_DATA).tag_ids is None


@pytest.mark.parametrize("field", ["title", "location", "event_date", "capacity"])
def test_update_event_rejects_null_for_required_fields(field: str):
    with pytest.raises(ValidationError, match=f"{field} cannot be null"):
        UpdateEventSchema(**{field: None})


def test_update_event_allows_null_text():
    schema = UpdateEventSchema(text=None)

    assert schema.model_dump(exclude_unset=True) == {"text": None}


def test_update_event_dumps_only_passed_fields():
    schema = UpdateEventSchema(title=EVENT_DATA["title"])

    assert schema.model_dump(exclude_unset=True) == {"title": EVENT_DATA["title"]}


def test_update_event_empty_body_has_no_changes():
    assert UpdateEventSchema().model_dump(exclude_unset=True) == {}


@pytest.mark.parametrize("tag_id", [0, -1])
def test_tag_ids_must_be_positive(tag_id: int):
    with pytest.raises(ValidationError):
        SetEventTagsSchema(tag_ids=[tag_id])


def test_filter_params_defaults():
    params = EventFilterParams()

    assert params.limit == 20
    assert params.offset == 0
    assert params.date_from is None
    assert params.date_to is None
    assert params.tag_ids is None


def test_filter_params_allow_equal_dates():
    moment = datetime(2026, 2, 1, tzinfo=UTC)

    params = EventFilterParams(date_from=moment, date_to=moment)

    assert params.date_from == params.date_to == moment


def test_filter_params_reject_inverted_date_range():
    with pytest.raises(ValidationError, match="date_from must be less than or equal to date_to"):
        EventFilterParams(
            date_from=datetime(2026, 3, 1, tzinfo=UTC),
            date_to=datetime(2026, 2, 1, tzinfo=UTC),
        )


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"limit": 0}, id="limit-zero"),
        pytest.param({"limit": 101}, id="limit-too-big"),
        pytest.param({"page": 0}, id="page-zero"),
    ],
)
def test_filter_params_reject_invalid_pagination(params: dict):
    with pytest.raises(ValidationError):
        EventFilterParams(**params)
