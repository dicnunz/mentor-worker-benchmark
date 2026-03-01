from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('apricot', 5), ('acorn', 2), ('apricot', 1), ('eagle', 10), ('acorn', -1), ('nova', 0), ('opal', -4)]
    assert rank_products(records, 3) == ['eagle', 'apricot', 'acorn']


def test_tie_breaks_alphabetically() -> None:
    records = [('apricot', 4), ('nova', 4), ('opal', 4), ('apricot', -1), ('nova', -1), ('acorn', 1)]
    assert rank_products(records, 2) == ['opal', 'apricot']


def test_non_positive_k_returns_empty() -> None:
    records = [('apricot', 5), ('acorn', 2), ('apricot', 1), ('eagle', 10), ('acorn', -1), ('nova', 0), ('opal', -4)]
    assert rank_products(records, 0) == []
