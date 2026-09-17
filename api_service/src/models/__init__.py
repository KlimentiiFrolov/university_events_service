__all__ = ("Base", "Tags", "User")

from .base import Base
from .tags import Tags
from .users import User
# обязательно импортировать сюда все созданные от Base модели, чтобы абстрактный родитеский класс зарегистрировал и видел их