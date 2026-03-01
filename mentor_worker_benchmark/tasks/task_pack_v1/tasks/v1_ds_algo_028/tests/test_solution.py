from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('xylem', 6), ('piper', 2), ('xylem', 1), ('oasis', 9), ('piper', -1), ('bravo', 0), ('vivid', -4)]
    assert rank_products(records, 3) == ['oasis', 'xylem', 'piper']


def test_tie_breaks_alphabetically() -> None:
    records = [('xylem', 4), ('bravo', 4), ('vivid', 4), ('xylem', -1), ('bravo', -1), ('piper', 1)]
    assert rank_products(records, 2) == ['vivid', 'bravo']


def test_non_positive_k_returns_empty() -> None:
    records = [('xylem', 6), ('piper', 2), ('xylem', 1), ('oasis', 9), ('piper', -1), ('bravo', 0), ('vivid', -4)]
    assert rank_products(records, 0) == []
