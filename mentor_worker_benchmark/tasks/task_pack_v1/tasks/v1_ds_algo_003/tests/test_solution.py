from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('horizon', 5), ('golf', 2), ('horizon', 1), ('willow', 10), ('golf', -1), ('cinder', 0), ('pearl', -4)]
    assert rank_products(records, 3) == ['willow', 'horizon', 'golf']


def test_tie_breaks_alphabetically() -> None:
    records = [('horizon', 4), ('cinder', 4), ('pearl', 4), ('horizon', -1), ('cinder', -1), ('golf', 1)]
    assert rank_products(records, 2) == ['pearl', 'cinder']


def test_non_positive_k_returns_empty() -> None:
    records = [('horizon', 5), ('golf', 2), ('horizon', 1), ('willow', 10), ('golf', -1), ('cinder', 0), ('pearl', -4)]
    assert rank_products(records, 0) == []
