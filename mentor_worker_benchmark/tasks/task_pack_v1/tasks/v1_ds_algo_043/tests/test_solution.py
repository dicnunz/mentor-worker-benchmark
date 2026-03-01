from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('xylem', 6), ('quest', 2), ('xylem', 1), ('lantern', 10), ('quest', -1), ('mango', 0), ('unity', -4)]
    assert rank_products(records, 3) == ['lantern', 'xylem', 'quest']


def test_tie_breaks_alphabetically() -> None:
    records = [('xylem', 4), ('mango', 4), ('unity', 4), ('xylem', -1), ('mango', -1), ('quest', 1)]
    assert rank_products(records, 2) == ['unity', 'mango']


def test_non_positive_k_returns_empty() -> None:
    records = [('xylem', 6), ('quest', 2), ('xylem', 1), ('lantern', 10), ('quest', -1), ('mango', 0), ('unity', -4)]
    assert rank_products(records, 0) == []
