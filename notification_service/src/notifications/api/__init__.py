from collections.abc import Sequence

from fastapi import APIRouter

from .notifications import router as notifications_router
from .tickets import router as tickets_router

router_list: Sequence[APIRouter] = (
    notifications_router,
    tickets_router,
)

# Префикс /ws: nginx проксирует его в сервис уведомлений
main_router = APIRouter(prefix="/ws")

for router in router_list:
    main_router.include_router(router)
