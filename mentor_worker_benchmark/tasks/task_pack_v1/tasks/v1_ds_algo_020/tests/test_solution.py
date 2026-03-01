from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('solace', 7), ('jade', 2), ('solace', 1), ('raven', 9), ('jade', -1), ('vertex', 0), ('beacon', -4)]
    assert rank_products(records, 3) == ['raven', 'solace', 'jade']


def test_tie_breaks_alphabetically() -> None:
    records = [('solace', 4), ('vertex', 4), ('beacon', 4), ('solace', -1), ('vertex', -1), ('jade', 1)]
    assert rank_products(records, 2) == ['beacon', 'solace']


def test_non_positive_k_returns_empty() -> None:
    records = [('solace', 7), ('jade', 2), ('solace', 1), ('raven', 9), ('jade', -1), ('vertex', 0), ('beacon', -4)]
    assert rank_products(records, 0) == []
