from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api import main_router
from src.core.uow import UnitOfWork, get_uow


@pytest.fixture
def test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(main_router)
    return app


@pytest.fixture
async def api_client(
    session_maker: async_sessionmaker[AsyncSession],
    test_app: FastAPI,
) -> AsyncGenerator[AsyncClient, None]:
    # Как в приложении: на каждый запрос своя сессия и своя транзакция с настоящим COMMIT,
    # подменяется только БД — тестовая из контейнера
    async def _override_uow():
        async with UnitOfWork(session_factory=session_maker) as uow:
            yield uow

    test_app.dependency_overrides[get_uow] = _override_uow

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test"
    ) as client:
        yield client

    test_app.dependency_overrides.clear()
