from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('breeze', 7), ('yankee', 2), ('breeze', 1), ('island', 10), ('yankee', -1), ('quartz', 0), ('wander', -4)]
    assert rank_products(records, 3) == ['island', 'breeze', 'yankee']


def test_tie_breaks_alphabetically() -> None:
    records = [('breeze', 4), ('quartz', 4), ('wander', 4), ('breeze', -1), ('quartz', -1), ('yankee', 1)]
    assert rank_products(records, 2) == ['wander', 'breeze']


def test_non_positive_k_returns_empty() -> None:
    records = [('breeze', 7), ('yankee', 2), ('breeze', 1), ('island', 10), ('yankee', -1), ('quartz', 0), ('wander', -4)]
    assert rank_products(records, 0) == []
