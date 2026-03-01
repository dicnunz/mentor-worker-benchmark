from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('yankee', 6), ('glider', 2), ('yankee', 1), ('thunder', 10), ('glider', -1), ('lantern', 0), ('xpress', -4)]
    assert rank_products(records, 3) == ['thunder', 'yankee', 'glider']


def test_tie_breaks_alphabetically() -> None:
    records = [('yankee', 4), ('lantern', 4), ('xpress', 4), ('yankee', -1), ('lantern', -1), ('glider', 1)]
    assert rank_products(records, 2) == ['xpress', 'lantern']


def test_non_positive_k_returns_empty() -> None:
    records = [('yankee', 6), ('glider', 2), ('yankee', 1), ('thunder', 10), ('glider', -1), ('lantern', 0), ('xpress', -4)]
    assert rank_products(records, 0) == []
