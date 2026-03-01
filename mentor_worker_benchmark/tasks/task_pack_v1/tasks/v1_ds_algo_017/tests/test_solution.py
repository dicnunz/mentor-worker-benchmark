from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('umber', 7), ('drift', 2), ('umber', 1), ('cobalt', 10), ('drift', -1), ('breeze', 0), ('lima', -4)]
    assert rank_products(records, 3) == ['cobalt', 'umber', 'drift']


def test_tie_breaks_alphabetically() -> None:
    records = [('umber', 4), ('breeze', 4), ('lima', 4), ('umber', -1), ('breeze', -1), ('drift', 1)]
    assert rank_products(records, 2) == ['lima', 'breeze']


def test_non_positive_k_returns_empty() -> None:
    records = [('umber', 7), ('drift', 2), ('umber', 1), ('cobalt', 10), ('drift', -1), ('breeze', 0), ('lima', -4)]
    assert rank_products(records, 0) == []
