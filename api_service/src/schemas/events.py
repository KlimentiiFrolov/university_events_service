from datetime import datetime
from typing import Annotated, Any, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from src.schemas.pagination import PaginationParams
from src.schemas.tags import TagResponse


def _unique(tag_ids: list[int]) -> list[int]:
    """Убрать повторы, сохранив порядок: дубль нарушил бы PK (event_id, tag_id) в event_tags."""
    return list(dict.fromkeys(tag_ids))


TagIds = Annotated[list[Annotated[int, Field(gt=0)]], AfterValidator(_unique)]


class CreateEventSchema(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    text: str | None = None
    location: str = Field(min_length=1, max_length=200)
    event_date: datetime
    capacity: int = Field(ge=0)
    tag_ids: TagIds | None = None


class UpdateEventSchema(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    text: str | None = None
    location: str | None = Field(default=None, min_length=1, max_length=200)
    event_date: datetime | None = None
    capacity: int | None = Field(default=None, ge=0)

    @field_validator("title", "location", "event_date", "capacity")
    @classmethod
    def reject_null(cls, value: Any, info: ValidationInfo) -> Any:
        # Валидатор не вызывается для значений по умолчанию, только для переданных явно
        if value is None:
            raise ValueError(f"{info.field_name} cannot be null")

        return value


class SetEventTagsSchema(BaseModel):
    tag_ids: TagIds


class EventFilterParams(PaginationParams):
    date_from: datetime | None = None
    date_to: datetime | None = None
    tag_ids: list[int] | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> Self:
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("date_from must be less than or equal to date_to")

        return self


class EventResponse(BaseModel):
    id: int
    title: str
    text: str | None
    location: str
    event_date: datetime
    capacity: int
    created_by_id: int
    created_at: datetime
    tags: list[TagResponse]


class EventListResponse(BaseModel):
    page: int
    total: int
    items: list[EventResponse]

