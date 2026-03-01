from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('golf', 6), ('elm', 2), ('golf', 1), ('harbor', 9), ('elm', -1), ('tango', 0), ('zenith', -4)]
    assert rank_products(records, 3) == ['harbor', 'golf', 'elm']


def test_tie_breaks_alphabetically() -> None:
    records = [('golf', 4), ('tango', 4), ('zenith', 4), ('golf', -1), ('tango', -1), ('elm', 1)]
    assert rank_products(records, 2) == ['zenith', 'golf']


def test_non_positive_k_returns_empty() -> None:
    records = [('golf', 6), ('elm', 2), ('golf', 1), ('harbor', 9), ('elm', -1), ('tango', 0), ('zenith', -4)]
    assert rank_products(records, 0) == []
