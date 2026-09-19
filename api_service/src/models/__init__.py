__all__ = ("Base", "Event", "EventTag", "Tag", "User)

from .base import Base
from .event_tags import EventTag
from .events import Event
from .tags import Tag
from .users import User
# обязательно импортировать сюда все созданные от Base модели, чтобы абстрактный родитеский класс зарегистрировал и видел их