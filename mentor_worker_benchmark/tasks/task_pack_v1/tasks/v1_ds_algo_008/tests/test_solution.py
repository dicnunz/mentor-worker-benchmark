from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('quiver', 7), ('yonder', 2), ('quiver', 1), ('canyon', 9), ('yonder', -1), ('zebra', 0), ('pearl', -4)]
    assert rank_products(records, 3) == ['canyon', 'quiver', 'yonder']


def test_tie_breaks_alphabetically() -> None:
    records = [('quiver', 4), ('zebra', 4), ('pearl', 4), ('quiver', -1), ('zebra', -1), ('yonder', 1)]
    assert rank_products(records, 2) == ['pearl', 'quiver']


def test_non_positive_k_returns_empty() -> None:
    records = [('quiver', 7), ('yonder', 2), ('quiver', 1), ('canyon', 9), ('yonder', -1), ('zebra', 0), ('pearl', -4)]
    assert rank_products(records, 0) == []
