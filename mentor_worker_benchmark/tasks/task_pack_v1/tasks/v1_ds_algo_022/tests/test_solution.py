from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('zenith', 6), ('apricot', 2), ('zenith', 1), ('ivory', 9), ('apricot', -1), ('vertex', 0), ('horizon', -4)]
    assert rank_products(records, 3) == ['ivory', 'zenith', 'apricot']


def test_tie_breaks_alphabetically() -> None:
    records = [('zenith', 4), ('vertex', 4), ('horizon', 4), ('zenith', -1), ('vertex', -1), ('apricot', 1)]
    assert rank_products(records, 2) == ['horizon', 'vertex']


def test_non_positive_k_returns_empty() -> None:
    records = [('zenith', 6), ('apricot', 2), ('zenith', 1), ('ivory', 9), ('apricot', -1), ('vertex', 0), ('horizon', -4)]
    assert rank_products(records, 0) == []
