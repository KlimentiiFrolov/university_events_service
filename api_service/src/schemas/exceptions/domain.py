class DomainError(Exception):
    """Базовая ошибка бизнес-логики."""


class NotFoundError(DomainError):
    def __init__(
        self,
        entity: str,
        identifier: int | str,
    ):
        self.entity = entity
        self.identifier = identifier

        super().__init__(
            f"{entity} with identifier={identifier} was not found"
        )


class ConflictError(DomainError):
    """Операция конфликтует с текущим состоянием данных."""


class RegistrationAlreadyExistsError(ConflictError):
    """Пользователь уже регистрировался на мероприятие."""


class RegistrationAlreadyCancelledError(ConflictError):
    """Регистрация уже отменена."""


class RegistrationAlreadyActiveError(ConflictError):
    """Регистрация уже активна."""


class EventCapacityExceededError(ConflictError):
    """На мероприятии больше нет свободных мест."""