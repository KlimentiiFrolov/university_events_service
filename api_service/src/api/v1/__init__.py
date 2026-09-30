from typing import Sequence

from fastapi import APIRouter

router_list: Sequence[APIRouter] = tuple()

v1_router = APIRouter(prefix="/v1")

for router in router_list:
    v1_router.include_router(router)
