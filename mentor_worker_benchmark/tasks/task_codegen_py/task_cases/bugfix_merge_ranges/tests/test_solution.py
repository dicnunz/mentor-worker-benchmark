from src.solution import merge_ranges


def test_merges_overlapping_ranges() -> None:
    assert merge_ranges([(1, 4), (2, 6), (8, 10)]) == [(1, 6), (8, 10)]


def test_merges_touching_ranges() -> None:
    assert merge_ranges([(1, 3), (4, 5), (9, 11), (12, 12)]) == [(1, 5), (9, 12)]


def test_handles_unsorted_input() -> None:
    assert merge_ranges([(10, 12), (1, 2), (2, 4)]) == [(1, 4), (10, 12)]
