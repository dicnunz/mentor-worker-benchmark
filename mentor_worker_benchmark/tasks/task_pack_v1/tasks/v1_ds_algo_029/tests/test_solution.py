from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('jasper', 7), ('mango', 2), ('jasper', 1), ('zen', 10), ('mango', -1), ('beacon', 0), ('island', -4)]
    assert rank_products(records, 3) == ['zen', 'jasper', 'mango']


def test_tie_breaks_alphabetically() -> None:
    records = [('jasper', 4), ('beacon', 4), ('island', 4), ('jasper', -1), ('beacon', -1), ('mango', 1)]
    assert rank_products(records, 2) == ['island', 'beacon']


def test_non_positive_k_returns_empty() -> None:
    records = [('jasper', 7), ('mango', 2), ('jasper', 1), ('zen', 10), ('mango', -1), ('beacon', 0), ('island', -4)]
    assert rank_products(records, 0) == []
