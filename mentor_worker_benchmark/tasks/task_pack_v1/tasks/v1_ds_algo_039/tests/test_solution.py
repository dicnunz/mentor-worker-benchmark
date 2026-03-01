from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('amber', 5), ('knight', 2), ('amber', 1), ('acorn', 10), ('knight', -1), ('lima', 0), ('drift', -4)]
    assert rank_products(records, 3) == ['acorn', 'amber', 'knight']


def test_tie_breaks_alphabetically() -> None:
    records = [('amber', 4), ('lima', 4), ('drift', 4), ('amber', -1), ('lima', -1), ('knight', 1)]
    assert rank_products(records, 2) == ['drift', 'amber']


def test_non_positive_k_returns_empty() -> None:
    records = [('amber', 5), ('knight', 2), ('amber', 1), ('acorn', 10), ('knight', -1), ('lima', 0), ('drift', -4)]
    assert rank_products(records, 0) == []
