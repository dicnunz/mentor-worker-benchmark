from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('mercury', 5), ('iris', 2), ('mercury', 1), ('harbor', 10), ('iris', -1), ('acorn', 0), ('yearling', -4)]
    assert rank_products(records, 3) == ['harbor', 'mercury', 'iris']


def test_tie_breaks_alphabetically() -> None:
    records = [('mercury', 4), ('acorn', 4), ('yearling', 4), ('mercury', -1), ('acorn', -1), ('iris', 1)]
    assert rank_products(records, 2) == ['yearling', 'acorn']


def test_non_positive_k_returns_empty() -> None:
    records = [('mercury', 5), ('iris', 2), ('mercury', 1), ('harbor', 10), ('iris', -1), ('acorn', 0), ('yearling', -4)]
    assert rank_products(records, 0) == []
