import pytest
from sqlalchemy.exc import IntegrityError

from src.core.uow import UnitOfWork
from src.models.tags import Tag


async def test_add_persists_tag_and_assigns_id(make_tag):
    name = "IT"

    tag = await make_tag(name=name)

    assert tag.id is not None
    assert tag.name == name


async def test_get_by_name_finds_tag(uow: UnitOfWork, make_tag):
    tag = await make_tag(name="Sport")

    fetched = await uow.tags.get_by_name(tag.name)

    assert fetched is not None
    assert fetched.id == tag.id


async def test_get_by_name_returns_none_when_missing(uow: UnitOfWork):
    assert await uow.tags.get_by_name("Missing") is None


async def test_list_by_names_returns_matching_tags(uow: UnitOfWork, make_tag):
    first = await make_tag(name="IT")
    second = await make_tag(name="Career")
    await make_tag(name="Sport")

    tags = await uow.tags.list_by_names([first.name, second.name])

    assert {tag.id for tag in tags} == {first.id, second.id}


async def test_list_by_ids_returns_matching_tags(uow: UnitOfWork, make_tag):
    first = await make_tag(name="IT")
    second = await make_tag(name="Career")
    await make_tag(name="Sport")

    tags = await uow.tags.list_by_ids([first.id, second.id])

    assert {tag.id for tag in tags} == {first.id, second.id}


async def test_add_duplicate_name_raises_integrity_error(uow: UnitOfWork, make_tag):
    await make_tag(name="IT")

    with pytest.raises(IntegrityError):
        await uow.tags.add(Tag(name="IT"))

    await uow.rollback()

async def test_add_too_short_name_raises_integrity_error(uow: UnitOfWork):
    with pytest.raises(IntegrityError):
        await uow.tags.add(Tag(name="a"))

    await uow.rollback()


async def test_get_by_name_finds_each_seeded_tag(
    uow: UnitOfWork,
    seed_tags: list[Tag],
):
    for tag in seed_tags:
        fetched = await uow.tags.get_by_name(tag.name)

        assert fetched is not None
        assert fetched.id == tag.id


@pytest.mark.parametrize(
    "selection",
    [
        pytest.param(slice(0, 1), id="one-tag"),
        pytest.param(slice(0, 2), id="two-tags"),
        pytest.param(slice(1, None), id="all-but-first"),
        pytest.param(slice(0, 0), id="no-tags"),
    ],
)
async def test_list_by_names_returns_requested_seeded_tags(
    uow: UnitOfWork,
    seed_tags: list[Tag],
    selection: slice,
):
    requested = seed_tags[selection]

    tags = await uow.tags.list_by_names([tag.name for tag in requested])

    assert {tag.id for tag in tags} == {tag.id for tag in requested}


async def test_list_by_names_ignores_missing_names(
    uow: UnitOfWork,
    seed_tags: list[Tag],
):
    missing_name = "missing-" + "-".join(tag.name for tag in seed_tags)

    tags = await uow.tags.list_by_names([missing_name])

    assert tags == []
