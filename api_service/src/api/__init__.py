from typing import Sequence

from fastapi import APIRouter

from .v1 import v1_router

router_list: Sequence[APIRouter] = (
    v1_router,
)

main_router = APIRouter(prefix="/api")

for router in router_list:
    main_router.include_router(router)
