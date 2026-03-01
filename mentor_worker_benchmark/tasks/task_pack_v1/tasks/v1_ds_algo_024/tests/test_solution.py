from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('elm', 5), ('fable', 2), ('elm', 1), ('canyon', 9), ('fable', -1), ('quill', 0), ('sunset', -4)]
    assert rank_products(records, 3) == ['canyon', 'elm', 'fable']


def test_tie_breaks_alphabetically() -> None:
    records = [('elm', 4), ('quill', 4), ('sunset', 4), ('elm', -1), ('quill', -1), ('fable', 1)]
    assert rank_products(records, 2) == ['sunset', 'elm']


def test_non_positive_k_returns_empty() -> None:
    records = [('elm', 5), ('fable', 2), ('elm', 1), ('canyon', 9), ('fable', -1), ('quill', 0), ('sunset', -4)]
    assert rank_products(records, 0) == []
