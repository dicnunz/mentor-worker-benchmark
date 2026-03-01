from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('kernel', 6), ('hotel', 2), ('kernel', 1), ('pearl', 10), ('hotel', -1), ('nebula', 0), ('ivory', -4)]
    assert rank_products(records, 3) == ['pearl', 'kernel', 'hotel']


def test_tie_breaks_alphabetically() -> None:
    records = [('kernel', 4), ('nebula', 4), ('ivory', 4), ('kernel', -1), ('nebula', -1), ('hotel', 1)]
    assert rank_products(records, 2) == ['ivory', 'kernel']


def test_non_positive_k_returns_empty() -> None:
    records = [('kernel', 6), ('hotel', 2), ('kernel', 1), ('pearl', 10), ('hotel', -1), ('nebula', 0), ('ivory', -4)]
    assert rank_products(records, 0) == []
