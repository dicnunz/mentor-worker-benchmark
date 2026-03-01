import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n feather , 8 , lima \\n onyx , 3 , pioneer \\n feather , 2 , jungle \\n onyx , oops , lima \\n maple , 9 , lima \\n  , 4 , pioneer \\n onyx , 7 , pioneer \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'feather': {'total': 10, 'count': 2, 'categories': ['jungle', 'lima']}, 'maple': {'total': 9, 'count': 1, 'categories': ['lima']}, 'onyx': {'total': 10, 'count': 2, 'categories': ['pioneer']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
