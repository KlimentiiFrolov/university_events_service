class DomainError(Exception):
    """Базовая ошибка бизнес-логики."""


class NotFoundError(DomainError):
    def __init__(self, entity: str, entity_id: int):
        self.entity = entity
        self.entity_id = entity_id

        super().__init__(
            f"{entity} with id={entity_id} was not found"
        )


class ConflictError(DomainError):
    """Операция конфликтует с текущим состоянием данных."""