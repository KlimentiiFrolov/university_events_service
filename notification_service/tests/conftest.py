import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from src.notifications.core.logger import log
from src.notifications.models import Base

log.handlers.clear()
log.propagate = True


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer("postgres:17") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def db_url(postgres_container: PostgresContainer) -> str:
    raw_url = postgres_container.get_connection_url()
    return raw_url.replace("postgresql+psycopg2", "postgresql+asyncpg", 1)


@pytest.fixture(scope="session")
def db_schema(db_url: str) -> None:
    """Схема создаётся один раз на весь прогон."""

    async def _create_schema() -> None:
        engine = create_async_engine(db_url, poolclass=NullPool)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_create_schema())


@pytest.fixture
async def engine(db_url: str, db_schema: None) -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(db_url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def clean_db(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            await connection.execute(table.delete())


@pytest.fixture
def session_maker(
    engine: AsyncEngine,
    clean_db: None,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture
async def session(
    session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_maker() as session:
        yield session
