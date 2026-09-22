from typing import Callable

from src.repositories.event_tags import EventTagRepository
from src.repositories.events import EventRepository
from src.repositories.registrations import RegistrationRepository
from src.repositories.roles import RoleRepository
from src.repositories.tags import TagRepository
from src.repositories.users import UserRepository

from .database import async_session_maker


class UnitOfWork:
    def __init__(self, session_factory: Callable = async_session_maker):
        self.session_factory = session_factory

    async def __aenter__(self):
        self.session = self.session_factory()

        self.users = UserRepository(self.session)
        self.events = EventRepository(self.session)
        self.tags = TagRepository(self.session)
        self.event_tags = EventTagRepository(self.session)
        self.registrations = RegistrationRepository(self.session)
        self.roles = RoleRepository(self.session)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                await self.rollback()
            else:
                await self.commit()
        except Exception:
            await self.rollback()
            raise
        finally:
            await self.session.close()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()


async def get_uow():
    async with UnitOfWork() as uow:
        yield uow
