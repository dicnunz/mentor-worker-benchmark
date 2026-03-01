from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('blossom', 7), ('echo', 2), ('blossom', 1), ('ember', 9), ('echo', -1), ('quest', 0), ('nectarine', -4)]
    assert rank_products(records, 3) == ['ember', 'blossom', 'echo']


def test_tie_breaks_alphabetically() -> None:
    records = [('blossom', 4), ('quest', 4), ('nectarine', 4), ('blossom', -1), ('quest', -1), ('echo', 1)]
    assert rank_products(records, 2) == ['nectarine', 'blossom']


def test_non_positive_k_returns_empty() -> None:
    records = [('blossom', 7), ('echo', 2), ('blossom', 1), ('ember', 9), ('echo', -1), ('quest', 0), ('nectarine', -4)]
    assert rank_products(records, 0) == []
