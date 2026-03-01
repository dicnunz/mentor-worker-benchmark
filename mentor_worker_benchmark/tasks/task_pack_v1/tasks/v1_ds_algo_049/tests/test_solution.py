from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('blossom', 6), ('ivory', 2), ('blossom', 1), ('zephyr', 10), ('ivory', -1), ('xenon', 0), ('quill', -4)]
    assert rank_products(records, 3) == ['zephyr', 'blossom', 'ivory']


def test_tie_breaks_alphabetically() -> None:
    records = [('blossom', 4), ('xenon', 4), ('quill', 4), ('blossom', -1), ('xenon', -1), ('ivory', 1)]
    assert rank_products(records, 2) == ['quill', 'blossom']


def test_non_positive_k_returns_empty() -> None:
    records = [('blossom', 6), ('ivory', 2), ('blossom', 1), ('zephyr', 10), ('ivory', -1), ('xenon', 0), ('quill', -4)]
    assert rank_products(records, 0) == []
