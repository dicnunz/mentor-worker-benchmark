from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('quest', 6), ('kepler', 2), ('quest', 1), ('drift', 10), ('kepler', -1), ('breeze', 0), ('solace', -4)]
    assert rank_products(records, 3) == ['drift', 'quest', 'kepler']


def test_tie_breaks_alphabetically() -> None:
    records = [('quest', 4), ('breeze', 4), ('solace', 4), ('quest', -1), ('breeze', -1), ('kepler', 1)]
    assert rank_products(records, 2) == ['solace', 'breeze']


def test_non_positive_k_returns_empty() -> None:
    records = [('quest', 6), ('kepler', 2), ('quest', 1), ('drift', 10), ('kepler', -1), ('breeze', 0), ('solace', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
