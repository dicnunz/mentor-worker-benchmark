from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('cobalt', 7), ('yankee', 2), ('cobalt', 1), ('dynamo', 9), ('yankee', -1), ('quill', 0), ('jasper', -4)]
    assert rank_products(records, 3) == ['dynamo', 'cobalt', 'yankee']


def test_tie_breaks_alphabetically() -> None:
    records = [('cobalt', 4), ('quill', 4), ('jasper', 4), ('cobalt', -1), ('quill', -1), ('yankee', 1)]
    assert rank_products(records, 2) == ['jasper', 'cobalt']


def test_non_positive_k_returns_empty() -> None:
    records = [('cobalt', 7), ('yankee', 2), ('cobalt', 1), ('dynamo', 9), ('yankee', -1), ('quill', 0), ('jasper', -4)]
    assert rank_products(records, 0) == []
