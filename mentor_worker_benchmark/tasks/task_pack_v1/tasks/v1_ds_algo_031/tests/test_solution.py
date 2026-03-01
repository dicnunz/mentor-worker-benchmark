from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('galaxy', 6), ('charlie', 2), ('galaxy', 1), ('eagle', 10), ('charlie', -1), ('juliet', 0), ('dynamo', -4)]
    assert rank_products(records, 3) == ['eagle', 'galaxy', 'charlie']


def test_tie_breaks_alphabetically() -> None:
    records = [('galaxy', 4), ('juliet', 4), ('dynamo', 4), ('galaxy', -1), ('juliet', -1), ('charlie', 1)]
    assert rank_products(records, 2) == ['dynamo', 'galaxy']


def test_non_positive_k_returns_empty() -> None:
    records = [('galaxy', 6), ('charlie', 2), ('galaxy', 1), ('eagle', 10), ('charlie', -1), ('juliet', 0), ('dynamo', -4)]
    assert rank_products(records, 0) == []
