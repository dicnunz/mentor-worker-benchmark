from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('vertex', 5), ('iris', 2), ('vertex', 1), ('rocket', 9), ('iris', -1), ('lantern', 0), ('utopia', -4)]
    assert rank_products(records, 3) == ['rocket', 'vertex', 'iris']


def test_tie_breaks_alphabetically() -> None:
    records = [('vertex', 4), ('lantern', 4), ('utopia', 4), ('vertex', -1), ('lantern', -1), ('iris', 1)]
    assert rank_products(records, 2) == ['utopia', 'lantern']


def test_non_positive_k_returns_empty() -> None:
    records = [('vertex', 5), ('iris', 2), ('vertex', 1), ('rocket', 9), ('iris', -1), ('lantern', 0), ('utopia', -4)]
    assert rank_products(records, 0) == []
