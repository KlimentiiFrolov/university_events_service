import pytest
from sqlalchemy.exc import IntegrityError

from src.core.uow import UnitOfWork


async def test_add_tags_creates_links(uow: UnitOfWork, make_event, make_tag):
    event = await make_event()
    tag_a = await make_tag(name="IT")
    tag_b = await make_tag(name="Career")

    links = await uow.event_tags.add_tags(event.id, [tag_a.id, tag_b.id])

    assert {link.tag_id for link in links} == {tag_a.id, tag_b.id}


async def test_get_by_event_and_tag_finds_existing_link(uow: UnitOfWork, make_event, make_tag):
    event = await make_event()
    tag = await make_tag()
    await uow.event_tags.add_tags(event.id, [tag.id])

    link = await uow.event_tags.get_by_event_and_tag(event.id, tag.id)

    assert link is not None
    assert link.event_id == event.id
    assert link.tag_id == tag.id


async def test_get_by_event_and_tag_returns_none_when_missing(
    uow: UnitOfWork, make_event, make_tag
):
    event = await make_event()
    tag = await make_tag()

    assert await uow.event_tags.get_by_event_and_tag(event.id, tag.id) is None


async def test_list_by_event_returns_all_tags_of_event(uow: UnitOfWork, make_event, make_tag):
    event = await make_event()
    tag_a = await make_tag(name="IT")
    tag_b = await make_tag(name="Career")
    await uow.event_tags.add_tags(event.id, [tag_a.id, tag_b.id])

    links = await uow.event_tags.list_by_event(event.id)

    assert {link.tag_id for link in links} == {tag_a.id, tag_b.id}


async def test_list_by_tag_returns_all_events_with_tag(uow: UnitOfWork, make_event, make_tag):
    tag = await make_tag()
    event_a = await make_event(title="A")
    event_b = await make_event(title="B")
    await uow.event_tags.add_tags(event_a.id, [tag.id])
    await uow.event_tags.add_tags(event_b.id, [tag.id])

    links = await uow.event_tags.list_by_tag(tag.id)

    assert {link.event_id for link in links} == {event_a.id, event_b.id}


async def test_replace_tags_swaps_the_full_set(uow: UnitOfWork, make_event, make_tag):
    event = await make_event()
    old_tag = await make_tag(name="Old")
    new_tag = await make_tag(name="New")
    await uow.event_tags.add_tags(event.id, [old_tag.id])

    await uow.event_tags.replace_tags(event.id, [new_tag.id])

    links = await uow.event_tags.list_by_event(event.id)
    assert {link.tag_id for link in links} == {new_tag.id}


async def test_delete_by_event_removes_all_links(uow: UnitOfWork, make_event, make_tag):
    event = await make_event()
    tag = await make_tag()
    await uow.event_tags.add_tags(event.id, [tag.id])

    await uow.event_tags.delete_by_event(event.id)

    assert await uow.event_tags.list_by_event(event.id) == []


async def test_add_duplicate_link_raises_integrity_error(uow: UnitOfWork, make_event, make_tag):
    event = await make_event()
    tag = await make_tag()
    await uow.event_tags.add_tags(event.id, [tag.id])

    with pytest.raises(IntegrityError):
        await uow.event_tags.add_tags(event.id, [tag.id])

    await uow.rollback() # явно делаем rollback т.к. with pytest.raises съедает исключение и по итогу UoW его не видит
