from src.solution import unique_preserve_order


def test_preserves_first_seen_order() -> None:
    assert unique_preserve_order(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]


def test_supports_unhashable_items() -> None:
    items = [{"k": 1}, {"k": 1}, {"k": 2}]
    assert unique_preserve_order(items) == [{"k": 1}, {"k": 2}]
