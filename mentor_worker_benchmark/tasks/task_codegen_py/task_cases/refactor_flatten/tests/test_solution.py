from src.solution import flatten


def test_flattens_nested_lists_and_tuples() -> None:
    assert flatten([1, [2, (3, 4)], 5]) == [1, 2, 3, 4, 5]


def test_no_state_leak_across_calls() -> None:
    first = flatten([1, [2]])
    second = flatten([3])
    assert first == [1, 2]
    assert second == [3]


def test_empty_input() -> None:
    assert flatten([]) == []
