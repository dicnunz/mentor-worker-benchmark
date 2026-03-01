from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('hazel', 5), ('elm', 2), ('hazel', 1), ('foxtrot', 9), ('elm', -1), ('oasis', 0), ('harbor', -4)]
    assert rank_products(records, 3) == ['foxtrot', 'hazel', 'elm']


def test_tie_breaks_alphabetically() -> None:
    records = [('hazel', 4), ('oasis', 4), ('harbor', 4), ('hazel', -1), ('oasis', -1), ('elm', 1)]
    assert rank_products(records, 2) == ['harbor', 'hazel']


def test_non_positive_k_returns_empty() -> None:
    records = [('hazel', 5), ('elm', 2), ('hazel', 1), ('foxtrot', 9), ('elm', -1), ('oasis', 0), ('harbor', -4)]
    assert rank_products(records, 0) == []
