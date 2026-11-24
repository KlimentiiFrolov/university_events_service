from fastapi import APIRouter, status

from notifications.dependencies import AuthSettingsDep, CurrentUserIdDep, TicketStoreDep
from notifications.schemas.tickets import WsTicketResponse

router = APIRouter(
    prefix="/tickets",
    tags=["websocket"],
)


@router.post("", response_model=WsTicketResponse, status_code=status.HTTP_201_CREATED)
async def issue_ticket(
    user_id: CurrentUserIdDep,
    tickets: TicketStoreDep,
    auth: AuthSettingsDep,
) -> WsTicketResponse:
    """Обменять access-токен на одноразовый тикет для подключения к /ws/notifications."""
    ticket = tickets.issue(user_id, auth.ws_ticket_ttl_seconds)
    return WsTicketResponse(ticket=ticket, expires_in=auth.ws_ticket_ttl_seconds)
