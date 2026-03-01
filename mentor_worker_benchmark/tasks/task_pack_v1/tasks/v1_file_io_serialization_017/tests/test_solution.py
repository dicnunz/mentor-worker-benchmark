import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n charlie , 6 , jasper \\n meadow , 3 , iris \\n charlie , 2 , xylem \\n meadow , oops , jasper \\n quest , 9 , jasper \\n  , 4 , iris \\n meadow , 7 , iris \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'charlie': {'total': 8, 'count': 2, 'categories': ['jasper', 'xylem']}, 'meadow': {'total': 10, 'count': 2, 'categories': ['iris']}, 'quest': {'total': 9, 'count': 1, 'categories': ['jasper']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
