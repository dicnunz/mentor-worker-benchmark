from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('iris', 7), ('xenon', 2), ('iris', 1), ('lima', 10), ('xenon', -1), ('prairie', 0), ('quartz', -4)]
    assert rank_products(records, 3) == ['lima', 'iris', 'xenon']


def test_tie_breaks_alphabetically() -> None:
    records = [('iris', 4), ('prairie', 4), ('quartz', 4), ('iris', -1), ('prairie', -1), ('xenon', 1)]
    assert rank_products(records, 2) == ['quartz', 'iris']


def test_non_positive_k_returns_empty() -> None:
    records = [('iris', 7), ('xenon', 2), ('iris', 1), ('lima', 10), ('xenon', -1), ('prairie', 0), ('quartz', -4)]
    assert rank_products(records, 0) == []
