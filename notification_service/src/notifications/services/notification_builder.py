"""Текст уведомления из сообщения api_service."""

from datetime import datetime

from pydantic import BaseModel

from notifications.schemas.messages import (
    EventNotificationData,
    EventType,
    NotificationMessage,
    RegistrationNotificationData,
)

# Названия полей мероприятия для текста event.updated
FIELD_NAMES = {
    "title": "название",
    "text": "описание",
    "location": "место",
    "event_date": "дата",
    "capacity": "количество мест",
}


class NotificationContent(BaseModel):
    title: str
    text: str


def format_date(value: datetime) -> str:
    return value.strftime("%d.%m.%Y %H:%M")


def build_notification(message: NotificationMessage) -> NotificationContent:
    """Заголовок и текст уведомления. Одинаковые для всех получателей сообщения."""
    match message.type:
        case EventType.REGISTRATION_CREATED:
            data = RegistrationNotificationData.model_validate(message.data)
            return NotificationContent(
                title="Новая запись на мероприятие",
                text=f"{data.participant_name} записался(-ась) на «{data.event_title}».",
            )

        case EventType.REGISTRATION_CANCELLED:
            data = RegistrationNotificationData.model_validate(message.data)
            return NotificationContent(
                title="Отмена записи на мероприятие",
                text=f"{data.participant_name} отменил(а) запись на «{data.event_title}».",
            )

        case EventType.EVENT_UPDATED:
            data = EventNotificationData.model_validate(message.data)
            fields = ", ".join(FIELD_NAMES.get(field, field) for field in data.changed_fields)
            return NotificationContent(
                title="Мероприятие изменено",
                text=(
                    f"В мероприятии «{data.event_title}» изменено: {fields}. "
                    f"Сейчас: {format_date(data.event_date)}, {data.location}."
                ),
            )

        case EventType.EVENT_CANCELLED:
            data = EventNotificationData.model_validate(message.data)
            return NotificationContent(
                title="Мероприятие отменено",
                text=(
                    f"Мероприятие «{data.event_title}» "
                    f"({format_date(data.event_date)}, {data.location}) отменено."
                ),
            )
