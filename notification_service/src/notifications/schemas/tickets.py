"""Выдача тикетов на подключение к WebSocket."""

from pydantic import BaseModel


class WsTicketResponse(BaseModel):
    ticket: str
    # Через сколько секунд тикет истечёт, если его не использовать
    expires_in: int
