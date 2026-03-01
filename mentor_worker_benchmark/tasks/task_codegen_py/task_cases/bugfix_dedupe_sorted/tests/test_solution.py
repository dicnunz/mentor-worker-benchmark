from src.solution import dedupe_sorted


def test_removes_duplicates() -> None:
    assert dedupe_sorted([1, 1, 2, 2, 2, 5, 9, 9]) == [1, 2, 5, 9]


def test_handles_single_value() -> None:
    assert dedupe_sorted([7]) == [7]


def test_handles_empty_list() -> None:
    assert dedupe_sorted([]) == []
