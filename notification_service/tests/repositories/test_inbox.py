from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from notifications.repositories.inbox import InboxRepository


async def test_new_message_is_added(session: AsyncSession):
    assert await InboxRepository(session).add_if_new(uuid4()) is True


async def test_repeated_message_is_rejected(session_maker: async_sessionmaker[AsyncSession]):
    message_id = uuid4()
    async with session_maker() as session, session.begin():
        await InboxRepository(session).add_if_new(message_id)

    async with session_maker() as session, session.begin():
        assert await InboxRepository(session).add_if_new(message_id) is False


async def test_different_messages_are_independent(session: AsyncSession):
    inbox = InboxRepository(session)

    assert await inbox.add_if_new(uuid4()) is True
    assert await inbox.add_if_new(uuid4()) is True
