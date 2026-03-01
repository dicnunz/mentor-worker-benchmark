from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('nebula', 5), ('grove', 2), ('nebula', 1), ('legend', 10), ('grove', -1), ('timber', 0), ('delta', -4)]
    assert rank_products(records, 3) == ['legend', 'nebula', 'grove']


def test_tie_breaks_alphabetically() -> None:
    records = [('nebula', 4), ('timber', 4), ('delta', 4), ('nebula', -1), ('timber', -1), ('grove', 1)]
    assert rank_products(records, 2) == ['delta', 'nebula']


def test_non_positive_k_returns_empty() -> None:
    records = [('nebula', 5), ('grove', 2), ('nebula', 1), ('legend', 10), ('grove', -1), ('timber', 0), ('delta', -4)]
    assert rank_products(records, 0) == []
