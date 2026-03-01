from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('drift', 6), ('blossom', 2), ('drift', 1), ('nova', 9), ('blossom', -1), ('utopia', 0), ('pearl', -4)]
    assert rank_products(records, 3) == ['nova', 'drift', 'blossom']


def test_tie_breaks_alphabetically() -> None:
    records = [('drift', 4), ('utopia', 4), ('pearl', 4), ('drift', -1), ('utopia', -1), ('blossom', 1)]
    assert rank_products(records, 2) == ['pearl', 'drift']


def test_non_positive_k_returns_empty() -> None:
    records = [('drift', 6), ('blossom', 2), ('drift', 1), ('nova', 9), ('blossom', -1), ('utopia', 0), ('pearl', -4)]
    assert rank_products(records, 0) == []
