from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from src.api import main_router
from src.core.uow import UnitOfWork, get_uow


@pytest.fixture
async def async_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    connection = await engine.connect()
    transaction = await connection.begin()

    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.fixture(autouse=True)
def _roles_seeded(seed_roles: None) -> None:
    """Роли создаются раньше остальных фикстур: seed_users и make_user ищут их в БД."""


@pytest.fixture
def test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(main_router)
    return app


@pytest.fixture
async def api_client(async_session, test_app):
    async def _override_uow():
        async with UnitOfWork(session_factory=lambda: async_session) as uow:
            yield uow

    test_app.dependency_overrides[get_uow] = _override_uow


    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test"
    ) as client:
        yield client

    test_app.dependency_overrides.clear()
