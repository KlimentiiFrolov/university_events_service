__all__ = ("Base", "Event", "EventTag", "Tag")

from .base import Base
from .event_tags import EventTag
from .events import Event
from .tags import Tag
# обязательно импортировать сюда все созданные от Base модели, чтобы абстрактный родитеский класс зарегистрировал и видел их