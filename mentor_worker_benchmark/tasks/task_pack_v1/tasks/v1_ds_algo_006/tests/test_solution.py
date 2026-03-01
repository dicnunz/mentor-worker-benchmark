from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('charlie', 5), ('drift', 2), ('charlie', 1), ('xpress', 9), ('drift', -1), ('vivid', 0), ('eagle', -4)]
    assert rank_products(records, 3) == ['xpress', 'charlie', 'drift']


def test_tie_breaks_alphabetically() -> None:
    records = [('charlie', 4), ('vivid', 4), ('eagle', 4), ('charlie', -1), ('vivid', -1), ('drift', 1)]
    assert rank_products(records, 2) == ['eagle', 'charlie']


def test_non_positive_k_returns_empty() -> None:
    records = [('charlie', 5), ('drift', 2), ('charlie', 1), ('xpress', 9), ('drift', -1), ('vivid', 0), ('eagle', -4)]
    assert rank_products(records, 0) == []
