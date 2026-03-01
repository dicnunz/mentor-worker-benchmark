from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('xenon', 7), ('lantern', 2), ('xenon', 1), ('quartz', 10), ('lantern', -1), ('jasper', 0), ('solace', -4)]
    assert rank_products(records, 3) == ['quartz', 'xenon', 'lantern']


def test_tie_breaks_alphabetically() -> None:
    records = [('xenon', 4), ('jasper', 4), ('solace', 4), ('xenon', -1), ('jasper', -1), ('lantern', 1)]
    assert rank_products(records, 2) == ['solace', 'jasper']


def test_non_positive_k_returns_empty() -> None:
    records = [('xenon', 7), ('lantern', 2), ('xenon', 1), ('quartz', 10), ('lantern', -1), ('jasper', 0), ('solace', -4)]
    assert rank_products(records, 0) == []
