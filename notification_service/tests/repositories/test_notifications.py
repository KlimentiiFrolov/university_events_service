from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from notifications.models import Notification
from notifications.repositories.notifications import NotificationRepository

USER_ID = 7
OTHER_USER_ID = 8


def make_notification(user_id: int = USER_ID, title: str = "Title") -> Notification:
    return Notification(
        message_id=uuid4(),
        user_id=user_id,
        type="registration.created",
        title=title,
        text="Text",
        data={"event_id": 1},
    )


async def test_add_many_assigns_ids(session: AsyncSession):
    notifications = await NotificationRepository(session).add_many(
        [make_notification(), make_notification()]
    )

    assert all(notification.id is not None for notification in notifications)
    assert all(notification.delivered_at is None for notification in notifications)


async def test_list_undelivered_returns_only_users_undelivered_in_order(session: AsyncSession):
    repository = NotificationRepository(session)
    first, delivered, second, _ = await repository.add_many([
        make_notification(title="first"),
        make_notification(title="delivered"),
        make_notification(title="second"),
        make_notification(user_id=OTHER_USER_ID),
    ])
    await repository.mark_delivered([delivered.id])

    undelivered = await repository.list_undelivered(USER_ID)

    assert [notification.id for notification in undelivered] == [first.id, second.id]


async def test_mark_delivered_sets_delivered_at_only_for_given_ids(session: AsyncSession):
    repository = NotificationRepository(session)
    marked, untouched = await repository.add_many([make_notification(), make_notification()])

    await repository.mark_delivered([marked.id])
    await session.refresh(marked)
    await session.refresh(untouched)

    assert marked.delivered_at is not None
    assert untouched.delivered_at is None


async def test_mark_delivered_keeps_first_delivery_time(session: AsyncSession):
    repository = NotificationRepository(session)
    notifications = await repository.add_many([make_notification()])
    notification = notifications[0]
    await repository.mark_delivered([notification.id])
    # now() - время начала транзакции: повтор в той же транзакции дал бы то же время
    await session.commit()
    await session.refresh(notification)
    first_delivery = notification.delivered_at

    await repository.mark_delivered([notification.id])
    await session.refresh(notification)

    assert notification.delivered_at == first_delivery


async def test_mark_delivered_with_empty_list_does_nothing(session: AsyncSession):
    await NotificationRepository(session).mark_delivered([])
