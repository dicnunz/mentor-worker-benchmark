from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('utopia', 6), ('acorn', 2), ('utopia', 1), ('maple', 10), ('acorn', -1), ('kilo', 0), ('solace', -4)]
    assert rank_products(records, 3) == ['maple', 'utopia', 'acorn']


def test_tie_breaks_alphabetically() -> None:
    records = [('utopia', 4), ('kilo', 4), ('solace', 4), ('utopia', -1), ('kilo', -1), ('acorn', 1)]
    assert rank_products(records, 2) == ['solace', 'kilo']


def test_non_positive_k_returns_empty() -> None:
    records = [('utopia', 6), ('acorn', 2), ('utopia', 1), ('maple', 10), ('acorn', -1), ('kilo', 0), ('solace', -4)]
    assert rank_products(records, 0) == []
