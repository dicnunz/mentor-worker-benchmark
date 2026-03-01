from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('ivory', 5), ('yearling', 2), ('ivory', 1), ('hotel', 10), ('yearling', -1), ('apricot', 0), ('acorn', -4)]
    assert rank_products(records, 3) == ['hotel', 'ivory', 'yearling']


def test_tie_breaks_alphabetically() -> None:
    records = [('ivory', 4), ('apricot', 4), ('acorn', 4), ('ivory', -1), ('apricot', -1), ('yearling', 1)]
    assert rank_products(records, 2) == ['acorn', 'apricot']


def test_non_positive_k_returns_empty() -> None:
    records = [('ivory', 5), ('yearling', 2), ('ivory', 1), ('hotel', 10), ('yearling', -1), ('apricot', 0), ('acorn', -4)]
    assert rank_products(records, 0) == []
