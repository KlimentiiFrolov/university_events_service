import pytest
from pydantic import ValidationError

from src.schemas.pagination import PaginationParams


@pytest.mark.parametrize(
    "page,limit,expected_offset",
    [
        pytest.param(1, 20, 0, id="first-page"),
        pytest.param(2, 20, 20, id="second-page"),
        pytest.param(3, 10, 20, id="third-page-small-limit"),
        pytest.param(5, 1, 4, id="limit-one"),
    ],
)
def test_offset_is_calculated_from_page_and_limit(page: int, limit: int, expected_offset: int):
    assert PaginationParams(page=page, limit=limit).offset == expected_offset


def test_defaults():
    params = PaginationParams()

    assert (params.page, params.limit, params.offset) == (1, 20, 0)


def test_model_dump_contains_offset_instead_of_page():
    assert PaginationParams(page=2, limit=10).model_dump() == {"limit": 10, "offset": 10}


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"page": 0}, id="page-zero"),
        pytest.param({"page": -1}, id="negative-page"),
        pytest.param({"limit": 0}, id="limit-zero"),
        pytest.param({"limit": 101}, id="limit-too-big"),
    ],
)
def test_rejects_invalid_values(params: dict):
    with pytest.raises(ValidationError):
        PaginationParams(**params)
