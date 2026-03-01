from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('apricot', 7), ('mercury', 2), ('apricot', 1), ('delta', 10), ('mercury', -1), ('india', 0), ('quiver', -4)]
    assert rank_products(records, 3) == ['delta', 'apricot', 'mercury']


def test_tie_breaks_alphabetically() -> None:
    records = [('apricot', 4), ('india', 4), ('quiver', 4), ('apricot', -1), ('india', -1), ('mercury', 1)]
    assert rank_products(records, 2) == ['quiver', 'apricot']


def test_non_positive_k_returns_empty() -> None:
    records = [('apricot', 7), ('mercury', 2), ('apricot', 1), ('delta', 10), ('mercury', -1), ('india', 0), ('quiver', -4)]
    assert rank_products(records, 0) == []
