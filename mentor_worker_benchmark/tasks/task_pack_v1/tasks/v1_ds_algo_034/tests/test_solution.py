from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('zephyr', 6), ('knight', 2), ('zephyr', 1), ('solace', 9), ('knight', -1), ('raven', 0), ('cobalt', -4)]
    assert rank_products(records, 3) == ['solace', 'zephyr', 'knight']


def test_tie_breaks_alphabetically() -> None:
    records = [('zephyr', 4), ('raven', 4), ('cobalt', 4), ('zephyr', -1), ('raven', -1), ('knight', 1)]
    assert rank_products(records, 2) == ['cobalt', 'raven']


def test_non_positive_k_returns_empty() -> None:
    records = [('zephyr', 6), ('knight', 2), ('zephyr', 1), ('solace', 9), ('knight', -1), ('raven', 0), ('cobalt', -4)]
    assert rank_products(records, 0) == []
