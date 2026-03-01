from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('ember', 7), ('solace', 2), ('ember', 1), ('river', 9), ('solace', -1), ('juliet', 0), ('ultra', -4)]
    assert rank_products(records, 3) == ['river', 'ember', 'solace']


def test_tie_breaks_alphabetically() -> None:
    records = [('ember', 4), ('juliet', 4), ('ultra', 4), ('ember', -1), ('juliet', -1), ('solace', 1)]
    assert rank_products(records, 2) == ['ultra', 'ember']


def test_non_positive_k_returns_empty() -> None:
    records = [('ember', 7), ('solace', 2), ('ember', 1), ('river', 9), ('solace', -1), ('juliet', 0), ('ultra', -4)]
    assert rank_products(records, 0) == []
