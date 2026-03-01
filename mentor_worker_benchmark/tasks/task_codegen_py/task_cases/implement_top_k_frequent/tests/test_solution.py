from src.solution import top_k_frequent


def test_basic_frequency_ranking() -> None:
    words = ["apple", "banana", "apple", "pear", "banana", "apple"]
    assert top_k_frequent(words, 2) == ["apple", "banana"]


def test_tie_break_alphabetically() -> None:
    words = ["c", "b", "a", "b", "c", "a"]
    assert top_k_frequent(words, 3) == ["a", "b", "c"]


def test_k_larger_than_unique_count() -> None:
    assert top_k_frequent(["x", "y", "x"], 10) == ["x", "y"]
