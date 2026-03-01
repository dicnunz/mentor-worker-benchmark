from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('willow', 6), ('delta', 2), ('willow', 1), ('island', 9), ('delta', -1), ('iris', 0), ('unity', -4)]
    assert rank_products(records, 3) == ['island', 'willow', 'delta']


def test_tie_breaks_alphabetically() -> None:
    records = [('willow', 4), ('iris', 4), ('unity', 4), ('willow', -1), ('iris', -1), ('delta', 1)]
    assert rank_products(records, 2) == ['unity', 'iris']


def test_non_positive_k_returns_empty() -> None:
    records = [('willow', 6), ('delta', 2), ('willow', 1), ('island', 9), ('delta', -1), ('iris', 0), ('unity', -4)]
    assert rank_products(records, 0) == []
