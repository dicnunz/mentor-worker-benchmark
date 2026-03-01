from src.solution import sum_positive


def test_ignores_negative_values() -> None:
    assert sum_positive([1, -2, 3, -4, 0]) == 4


def test_all_negative_returns_zero() -> None:
    assert sum_positive([-3, -1, -99]) == 0


def test_empty_list_returns_zero() -> None:
    assert sum_positive([]) == 0
