from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('ripple', 5), ('xylem', 2), ('ripple', 1), ('elm', 9), ('xylem', -1), ('piper', 0), ('juliet', -4)]
    assert rank_products(records, 3) == ['elm', 'ripple', 'xylem']


def test_tie_breaks_alphabetically() -> None:
    records = [('ripple', 4), ('piper', 4), ('juliet', 4), ('ripple', -1), ('piper', -1), ('xylem', 1)]
    assert rank_products(records, 2) == ['juliet', 'piper']


def test_non_positive_k_returns_empty() -> None:
    records = [('ripple', 5), ('xylem', 2), ('ripple', 1), ('elm', 9), ('xylem', -1), ('piper', 0), ('juliet', -4)]
    assert rank_products(records, 0) == []
