from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('jasper', 7), ('mercury', 2), ('jasper', 1), ('golf', 10), ('mercury', -1), ('mango', 0), ('xylem', -4)]
    assert rank_products(records, 3) == ['golf', 'jasper', 'mercury']


def test_tie_breaks_alphabetically() -> None:
    records = [('jasper', 4), ('mango', 4), ('xylem', 4), ('jasper', -1), ('mango', -1), ('mercury', 1)]
    assert rank_products(records, 2) == ['xylem', 'jasper']


def test_non_positive_k_returns_empty() -> None:
    records = [('jasper', 7), ('mercury', 2), ('jasper', 1), ('golf', 10), ('mercury', -1), ('mango', 0), ('xylem', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
