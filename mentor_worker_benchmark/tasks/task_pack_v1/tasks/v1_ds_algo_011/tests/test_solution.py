from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('delta', 7), ('ultra', 2), ('delta', 1), ('xpress', 10), ('ultra', -1), ('orion', 0), ('pioneer', -4)]
    assert rank_products(records, 3) == ['xpress', 'delta', 'ultra']


def test_tie_breaks_alphabetically() -> None:
    records = [('delta', 4), ('orion', 4), ('pioneer', 4), ('delta', -1), ('orion', -1), ('ultra', 1)]
    assert rank_products(records, 2) == ['pioneer', 'delta']


def test_non_positive_k_returns_empty() -> None:
    records = [('delta', 7), ('ultra', 2), ('delta', 1), ('xpress', 10), ('ultra', -1), ('orion', 0), ('pioneer', -4)]
    assert rank_products(records, 0) == []
