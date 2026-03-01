from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('cobalt', 5), ('yonder', 2), ('cobalt', 1), ('delta', 10), ('yonder', -1), ('pearl', 0), ('cinder', -4)]
    assert rank_products(records, 3) == ['delta', 'cobalt', 'yonder']


def test_tie_breaks_alphabetically() -> None:
    records = [('cobalt', 4), ('pearl', 4), ('cinder', 4), ('cobalt', -1), ('pearl', -1), ('yonder', 1)]
    assert rank_products(records, 2) == ['cinder', 'cobalt']


def test_non_positive_k_returns_empty() -> None:
    records = [('cobalt', 5), ('yonder', 2), ('cobalt', 1), ('delta', 10), ('yonder', -1), ('pearl', 0), ('cinder', -4)]
    assert rank_products(records, 0) == []
