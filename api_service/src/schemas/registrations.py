from datetime import datetime

from pydantic import BaseModel

from src.models.registrations import RegistrationStatus


class RegistrationResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    status: RegistrationStatus
    registered_at: datetime
    cancelled_at: datetime | None


class RegistrationListResponse(BaseModel):
    total: int
    items: list[RegistrationResponse]


class ParticipantResponse(BaseModel):
    id: int
    email: str
    first_name: str
    second_name: str


class ParticipantListResponse(BaseModel):
    total: int
    items: list[ParticipantResponse]