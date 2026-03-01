import pytest

from src.solution import chunked


def test_even_chunks() -> None:
    assert chunked([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_trailing_short_chunk() -> None:
    assert chunked([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_invalid_chunk_size() -> None:
    with pytest.raises(ValueError):
        chunked([1, 2], 0)
