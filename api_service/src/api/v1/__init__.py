from typing import Sequence

from fastapi import APIRouter

from .auth import router as auth_router

router_list: Sequence[APIRouter] = (
    auth_router,
)

v1_router = APIRouter(prefix="/v1")

for router in router_list:
    v1_router.include_router(router)