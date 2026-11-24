from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Импорт через notifications, а не src.notifications: роутеры ссылаются на
# notifications.dependencies, и подмена из другого пути импорта не сработала бы
from notifications.api import main_router
from notifications.core.config import RabbitMQSettings
from notifications.dependencies import get_auth_settings
from notifications.lifespan import NotificationLifespan

from ..tokens import AUTH


@pytest.fixture
def app_session_maker(db_url: str, clean_db: None) -> async_sessionmaker[AsyncSession]:
    # NullPool: приложение работает в потоке TestClient со своим event loop,
    # соединения из пула другого loop asyncpg не примет
    engine = create_async_engine(db_url, poolclass=NullPool)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def notification_lifespan(
    app_session_maker: async_sessionmaker[AsyncSession],
) -> NotificationLifespan:
    # Без start(): RabbitMQ эндпоинтам не нужен
    return NotificationLifespan(RabbitMQSettings.model_construct(), session_factory=app_session_maker)


@pytest.fixture
def client(notification_lifespan: NotificationLifespan) -> Generator[TestClient, None, None]:
    app = FastAPI()
    app.include_router(main_router)
    app.dependency_overrides[get_auth_settings] = lambda: AUTH
    notification_lifespan.bind(app)
    with TestClient(app) as test_client:
        yield test_client
