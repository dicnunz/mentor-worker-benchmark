import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n ember , 7 , meadow \\n breeze , 3 , zenith \\n ember , 2 , ivory \\n breeze , oops , meadow \\n juliet , 9 , meadow \\n  , 4 , zenith \\n breeze , 7 , zenith \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'breeze': {'total': 10, 'count': 2, 'categories': ['zenith']}, 'ember': {'total': 9, 'count': 2, 'categories': ['ivory', 'meadow']}, 'juliet': {'total': 9, 'count': 1, 'categories': ['meadow']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
