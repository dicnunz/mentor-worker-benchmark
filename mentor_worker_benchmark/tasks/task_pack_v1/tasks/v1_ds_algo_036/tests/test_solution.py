from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('wander', 5), ('thunder', 2), ('wander', 1), ('solace', 9), ('thunder', -1), ('kepler', 0), ('cobalt', -4)]
    assert rank_products(records, 3) == ['solace', 'wander', 'thunder']


def test_tie_breaks_alphabetically() -> None:
    records = [('wander', 4), ('kepler', 4), ('cobalt', 4), ('wander', -1), ('kepler', -1), ('thunder', 1)]
    assert rank_products(records, 2) == ['cobalt', 'kepler']


def test_non_positive_k_returns_empty() -> None:
    records = [('wander', 5), ('thunder', 2), ('wander', 1), ('solace', 9), ('thunder', -1), ('kepler', 0), ('cobalt', -4)]
    assert rank_products(records, 0) == []
