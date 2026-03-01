from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('delta', 5), ('island', 2), ('delta', 1), ('zenith', 9), ('island', -1), ('timber', 0), ('nectar', -4)]
    assert rank_products(records, 3) == ['zenith', 'delta', 'island']


def test_tie_breaks_alphabetically() -> None:
    records = [('delta', 4), ('timber', 4), ('nectar', 4), ('delta', -1), ('timber', -1), ('island', 1)]
    assert rank_products(records, 2) == ['nectar', 'delta']


def test_non_positive_k_returns_empty() -> None:
    records = [('delta', 5), ('island', 2), ('delta', 1), ('zenith', 9), ('island', -1), ('timber', 0), ('nectar', -4)]
    assert rank_products(records, 0) == []
