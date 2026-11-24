"""WebSocket уведомлений: тикет из POST /ws/tickets в Authorization: Bearer <ticket> или ?ticket=."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from notifications.dependencies import ConnectionManagerDep, SessionFactoryDep, WsUserIdDep
from notifications.websocket.delivery import push_undelivered

router = APIRouter()


@router.websocket("/notifications")
async def notifications_websocket(
    websocket: WebSocket,
    user_id: WsUserIdDep,
    manager: ConnectionManagerDep,
    session_factory: SessionFactoryDep,
) -> None:
    await websocket.accept()
    # Регистрируемся до досылки: новое уведомление, сохранённое во время досылки,
    # не потеряется (в худшем случае придёт дважды - клиент отличает по id)
    manager.connect(user_id, websocket)
    try:
        await push_undelivered(manager, user_id, session_factory)

        # Клиент ничего не присылает; чтение нужно, чтобы заметить отключение
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, websocket)
