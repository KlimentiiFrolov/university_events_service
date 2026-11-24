from fastapi import APIRouter, status

from notifications.core.config import settings
from notifications.dependencies import CurrentUserIdDep, TicketStoreDep
from notifications.schemas.tickets import WsTicketResponse

router = APIRouter(
    prefix="/tickets",
    tags=["websocket"],
)


@router.post("", response_model=WsTicketResponse, status_code=status.HTTP_201_CREATED)
async def issue_ticket(
    user_id: CurrentUserIdDep,
    tickets: TicketStoreDep,
) -> WsTicketResponse:
    """Обменять access-токен на одноразовый тикет для подключения к /ws/notifications."""
    ttl_seconds = settings.auth.ws_ticket_ttl_seconds
    ticket = tickets.issue(user_id, ttl_seconds)
    return WsTicketResponse(ticket=ticket, expires_in=ttl_seconds)
