import asyncio
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy import NullPool, insert, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from src.core.logger import log
from src.core.passwords import hash_password
from src.core.uow import UnitOfWork
from src.models import Base
from src.models.event_tags import EventTag
from src.models.events import Event
from src.models.roles import Role, RoleName
from src.models.tags import Tag
from src.models.users import User
from src.services.events import EventService
from src.services.registrations import RegistrationService
from src.services.tags import TagService
from src.services.users import UserService

log.handlers.clear()
log.propagate = True

TEST_PASSWORD = "TestPassword123!"
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


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


@pytest.fixture(scope="function")
async def engine(db_url: str, db_schema: None) -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(db_url)

    yield engine

    await engine.dispose()

# На маленьких данных DELETE будет быстрее TRUNCATE
@pytest.fixture(scope="function")
async def clean_db(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            await connection.execute(table.delete())
        await connection.execute(
            insert(Role).values(
                [{"name": role_name} for role_name in RoleName]
            )
        )


@pytest.fixture(scope="function")
def session_maker(
    engine: AsyncEngine,
    clean_db: None,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture(scope="function")
async def async_session(
    session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_maker() as session:
        yield session


@pytest.fixture
async def uow(async_session: AsyncSession) -> AsyncGenerator[UnitOfWork, None]:
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
def event_service(uow: UnitOfWork) -> EventService:
    return EventService(uow=uow)


@pytest.fixture()
def tag_service(uow: UnitOfWork) -> TagService:
    return TagService(uow=uow)


@pytest.fixture()
def make_user(uow: UnitOfWork) -> Callable[..., Awaitable[User]]:
    async def _make_user(
        email: str | None = None,
        first_name: str = "Test",
        second_name: str = "User",
        role: RoleName = RoleName.PARTICIPANT,
        password_hash: str = TEST_PASSWORD_HASH,
    ) -> User:
        email = email or f"user-{uuid.uuid4().hex}@example.com"
        role_entity = await uow.roles.get_by_name(role)

        user = await uow.users.add(
            User(
                email=email,
                first_name=first_name,
                second_name=second_name,
                role=role_entity,
                password_hash=password_hash,
            )
        )
        await uow.commit()

        return user

    return _make_user


@pytest.fixture()
def make_tag(uow: UnitOfWork) -> Callable[..., Awaitable[Tag]]:
    async def _make_tag(name: str | None = None) -> Tag:
        name = name or f"tag-{uuid.uuid4().hex[:8]}"

        tag = await uow.tags.add(Tag(name=name))
        await uow.commit()

        return tag

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
            organizer = await make_user(role=RoleName.ORGANIZER)
            created_by_id = organizer.id

        event = await uow.events.add(
            Event(
                title=title,
                text="description",
                location=location,
                event_date=event_date or datetime(2026, 1, 1, tzinfo=UTC),
                capacity=capacity,
                created_by_id=created_by_id,
            )
        )
        await uow.commit()

        return event

    return _make_event


@pytest.fixture()
async def seed_users(async_session: AsyncSession) -> list[User]:
    participant_role = await async_session.scalar(
        select(Role).where(Role.name == RoleName.PARTICIPANT)
    )
    organizer_role = await async_session.scalar(
        select(Role).where(Role.name == RoleName.ORGANIZER)
    )

    users = [
        User(
            email="participant1@example.com",
            first_name="Participant",
            second_name="One",
            role=participant_role,
            password_hash=TEST_PASSWORD_HASH,
        ),
        User(
            email="participant2@example.com",
            first_name="Participant",
            second_name="Two",
            role=participant_role,
            password_hash=TEST_PASSWORD_HASH,
        ),
        User(
            email="organizer1@example.com",
            first_name="Organizer",
            second_name="One",
            role=organizer_role,
            password_hash=TEST_PASSWORD_HASH,
        ),
    ]

    async_session.add_all(users)
    await async_session.commit()

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
    organizer = next(
        user for user in seed_users if user.role.name == RoleName.ORGANIZER
    )

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
