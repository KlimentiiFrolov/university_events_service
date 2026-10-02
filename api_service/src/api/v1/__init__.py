from typing import Sequence

from fastapi import APIRouter

from .auth import router as auth_router
from .events import router as events_router
from .tags import router as tags_router

router_list: Sequence[APIRouter] = (
    auth_router,
    events_router,
    tags_router,
)

v1_router = APIRouter(prefix="/v1")

for router in router_list:
    v1_router.include_router(router)