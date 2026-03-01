from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('juliet', 7), ('yearling', 2), ('juliet', 1), ('orion', 10), ('yearling', -1), ('velvet', 0), ('hotel', -4)]
    assert rank_products(records, 3) == ['orion', 'juliet', 'yearling']


def test_tie_breaks_alphabetically() -> None:
    records = [('juliet', 4), ('velvet', 4), ('hotel', 4), ('juliet', -1), ('velvet', -1), ('yearling', 1)]
    assert rank_products(records, 2) == ['hotel', 'juliet']


def test_non_positive_k_returns_empty() -> None:
    records = [('juliet', 7), ('yearling', 2), ('juliet', 1), ('orion', 10), ('yearling', -1), ('velvet', 0), ('hotel', -4)]
    assert rank_products(records, 0) == []
