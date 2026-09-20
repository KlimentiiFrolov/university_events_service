import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from src.core.uow import UnitOfWork
from src.models import Base
from src.models.event_tags import EventTag
from src.models.events import Event
from src.models.tags import Tag
from src.models.users import User
from src.services.users import UserService
from src.services.registrations import RegistrationService


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer("postgres:17") as postgres:
        yield postgres


def create_db_url(postgres_container: PostgresContainer) -> str:
    raw_url = postgres_container.get_connection_url()
    return raw_url.replace("postgresql+psycopg2", "postgresql+asyncpg", 1)


@pytest.fixture(scope="function")
async def engine(postgres_container: PostgresContainer) -> AsyncGenerator[AsyncEngine, None]:
    """Создаёт движок и таблицы заново для каждого теста."""
    db_url = create_db_url(postgres_container)
    # NullPool, чтобы соединения не переиспользовались между тестами, запущенными в разных event loop
    engine = create_async_engine(db_url, poolclass=NullPool)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture(scope="function")
async def async_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Создаёт сессию, обёрнутую во внешнюю транзакцию, откатываемую после теста."""
    async_session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    connection = await engine.connect()
    transaction = await connection.begin()

    session = async_session_factory(bind=connection)

    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.fixture()
async def uow(async_session: AsyncSession) -> AsyncGenerator[UnitOfWork, None]:
    """UnitOfWork поверх сессии теста: commit() внутри теста коммитит только
    в рамках внешней транзакции async_session, которая в итоге откатывается."""
    unit_of_work = UnitOfWork(session_factory=lambda: async_session)

    async with unit_of_work:
        yield unit_of_work


@pytest.fixture()
def user_service(uow: UnitOfWork) -> UserService:
    return UserService(uow=uow)


@pytest.fixture()
def registration_service(uow: UnitOfWork) -> RegistrationService:
    return RegistrationService(uow=uow)


@pytest.fixture()
def make_user(uow: UnitOfWork) -> Callable[..., Awaitable[User]]:
    async def _make_user(
        email: str | None = None,
        first_name: str = "Test",
        second_name: str = "User",
        role: str = "participant",
    ) -> User:
        email = email or f"user-{uuid.uuid4().hex}@example.com"

        return await uow.users.add(
            User(
                email=email,
                first_name=first_name,
                second_name=second_name,
                role=role,
            )
        )

    return _make_user


@pytest.fixture()
def make_tag(uow: UnitOfWork) -> Callable[..., Awaitable[Tag]]:
    async def _make_tag(name: str | None = None) -> Tag:
        name = name or f"tag-{uuid.uuid4().hex[:8]}"
        return await uow.tags.add(Tag(name=name))

    return _make_tag


@pytest.fixture()
def make_event(
    uow: UnitOfWork,
    make_user: Callable[..., Awaitable[User]],
) -> Callable[..., Awaitable[Event]]:
    async def _make_event(
        *,
        title: str = "Event",
        location: str = "Main Hall",
        event_date: datetime | None = None,
        capacity: int = 10,
        created_by_id: int | None = None,
    ) -> Event:
        if created_by_id is None:
            organizer = await make_user(role="organizer")
            created_by_id = organizer.id

        return await uow.events.add(
            Event(
                title=title,
                text="description",
                location=location,
                event_date=event_date or datetime(2026, 1, 1, tzinfo=UTC),
                capacity=capacity,
                created_by_id=created_by_id,
            )
        )

    return _make_event


@pytest.fixture()
async def seed_users(async_session: AsyncSession) -> list[User]:
    users = [
        User(
            email="participant1@example.com",
            first_name="Participant",
            second_name="One",
            role="participant",
        ),
        User(
            email="participant2@example.com",
            first_name="Participant",
            second_name="Two",
            role="participant",
        ),
        User(
            email="organizer1@example.com",
            first_name="Organizer",
            second_name="One",
            role="organizer",
        ),
    ]

    async_session.add_all(users)
    await async_session.flush()

    return users


@pytest.fixture()
async def seed_tags(async_session: AsyncSession) -> list[Tag]:
    tags = [
        Tag(name="IT"),
        Tag(name="Career"),
        Tag(name="Sport"),
    ]

    async_session.add_all(tags)
    await async_session.commit()

    return tags


@pytest.fixture()
async def seed_events(async_session: AsyncSession, seed_users: list[User]) -> list[Event]:
    organizer = next(user for user in seed_users if user.role == "organizer")

    events = [
        Event(
            title="Lecture",
            text="Introductory lecture",
            location="Room 101",
            event_date=datetime(2026, 1, 10, tzinfo=UTC),
            capacity=30,
            created_by_id=organizer.id,
        ),
        Event(
            title="Hackathon",
            text="24h hackathon",
            location="Main Hall",
            event_date=datetime(2026, 2, 15, tzinfo=UTC),
            capacity=100,
            created_by_id=organizer.id,
        ),
        Event(
            title="Workshop",
            text="Hands-on workshop",
            location="Room 202",
            event_date=datetime(2026, 3, 20, tzinfo=UTC),
            capacity=20,
            created_by_id=organizer.id,
        ),
    ]

    async_session.add_all(events)
    await async_session.commit()

    return events


@pytest.fixture()
async def seed_event_tags(
    async_session: AsyncSession,
    seed_events: list[Event],
    seed_tags: list[Tag],
) -> list[EventTag]:
    lecture, hackathon, workshop = seed_events
    it, career, sport = seed_tags

    event_tags = [
        EventTag(event_id=lecture.id, tag_id=it.id),
        EventTag(event_id=hackathon.id, tag_id=it.id),
        EventTag(event_id=hackathon.id, tag_id=career.id),
        EventTag(event_id=workshop.id, tag_id=sport.id),
    ]

    async_session.add_all(event_tags)
    await async_session.commit()

    return event_tags
