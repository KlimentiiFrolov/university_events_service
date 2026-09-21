from datetime import datetime

from pydantic import BaseModel, Field


class CreateEventSchema(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    text: str | None = None
    location: str = Field(min_length=1, max_length=200)
    event_date: datetime
    capacity: int = Field(ge=0)
    tag_ids: list[int] | None = None


class UpdateEventSchema(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    text: str | None = None
    location: str | None = Field(default=None, min_length=1, max_length=200)
    event_date: datetime | None = None
    capacity: int | None = Field(default=None, ge=0)
