from datetime import UTC, datetime


def get_current_datetime() -> datetime:
    return datetime.now(UTC)