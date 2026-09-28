import pytest
from sqlalchemy.exc import IntegrityError

from src.core.uow import UnitOfWork
from src.models.tags import Tag


async def test_add_persists_tag_and_assigns_id(make_tag):
    tag = await make_tag(name="IT")

    assert tag.id is not None
    assert tag.name == "IT"


async def test_get_by_name_finds_tag(uow: UnitOfWork, make_tag):
    await make_tag(name="Sport")

    fetched = await uow.tags.get_by_name("Sport")

    assert fetched is not None
    assert fetched.name == "Sport"


async def test_get_by_name_returns_none_when_missing(uow: UnitOfWork):
    assert await uow.tags.get_by_name("Missing") is None


async def test_list_by_names_returns_matching_tags(uow: UnitOfWork, make_tag):
    await make_tag(name="IT")
    await make_tag(name="Career")
    await make_tag(name="Sport")

    tags = await uow.tags.list_by_names(["IT", "Career"])

    assert {tag.name for tag in tags} == {"IT", "Career"}


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


@pytest.mark.parametrize("index", [0, 1, 2])
async def test_get_by_name_finds_each_seeded_tag(
    uow: UnitOfWork,
    seed_tags: list[Tag],
    index: int,
):
    tag = seed_tags[index]

    fetched = await uow.tags.get_by_name(tag.name)

    assert fetched is not None
    assert fetched.id == tag.id


@pytest.mark.parametrize(
    "names,expected_names",
    [
        (["IT"], {"IT"}),
        (["IT", "Career"], {"IT", "Career"}),
        (["Sport", "Career"], {"Sport", "Career"}),
        (["Missing"], set()),
    ],
)
async def test_list_by_names_with_various_inputs(
    uow: UnitOfWork,
    seed_tags: list[Tag],
    names: list[str],
    expected_names: set[str],
):
    tags = await uow.tags.list_by_names(names)

    assert {tag.name for tag in tags} == expected_names
