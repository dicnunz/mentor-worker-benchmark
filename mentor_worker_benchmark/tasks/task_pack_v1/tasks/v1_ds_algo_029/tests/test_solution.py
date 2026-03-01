from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('pioneer', 7), ('meadow', 2), ('pioneer', 1), ('frost', 10), ('meadow', -1), ('thunder', 0), ('orion', -4)]
    assert rank_products(records, 3) == ['frost', 'pioneer', 'meadow']


def test_tie_breaks_alphabetically() -> None:
    records = [('pioneer', 4), ('thunder', 4), ('orion', 4), ('pioneer', -1), ('thunder', -1), ('meadow', 1)]
    assert rank_products(records, 2) == ['orion', 'pioneer']


def test_non_positive_k_returns_empty() -> None:
    records = [('pioneer', 7), ('meadow', 2), ('pioneer', 1), ('frost', 10), ('meadow', -1), ('thunder', 0), ('orion', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
