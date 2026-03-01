from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('wander', 6), ('canyon', 2), ('wander', 1), ('tango', 10), ('canyon', -1), ('drift', 0), ('timber', -4)]
    assert rank_products(records, 3) == ['tango', 'wander', 'canyon']


def test_tie_breaks_alphabetically() -> None:
    records = [('wander', 4), ('drift', 4), ('timber', 4), ('wander', -1), ('drift', -1), ('canyon', 1)]
    assert rank_products(records, 2) == ['timber', 'drift']


def test_non_positive_k_returns_empty() -> None:
    records = [('wander', 6), ('canyon', 2), ('wander', 1), ('tango', 10), ('canyon', -1), ('drift', 0), ('timber', -4)]
    assert rank_products(records, 0) == []
