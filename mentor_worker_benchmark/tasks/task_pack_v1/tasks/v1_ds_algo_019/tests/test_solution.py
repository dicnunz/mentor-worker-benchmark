from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('galaxy', 6), ('horizon', 2), ('galaxy', 1), ('dawn', 10), ('horizon', -1), ('lima', 0), ('nova', -4)]
    assert rank_products(records, 3) == ['dawn', 'galaxy', 'horizon']


def test_tie_breaks_alphabetically() -> None:
    records = [('galaxy', 4), ('lima', 4), ('nova', 4), ('galaxy', -1), ('lima', -1), ('horizon', 1)]
    assert rank_products(records, 2) == ['nova', 'galaxy']


def test_non_positive_k_returns_empty() -> None:
    records = [('galaxy', 6), ('horizon', 2), ('galaxy', 1), ('dawn', 10), ('horizon', -1), ('lima', 0), ('nova', -4)]
    assert rank_products(records, 0) == []
