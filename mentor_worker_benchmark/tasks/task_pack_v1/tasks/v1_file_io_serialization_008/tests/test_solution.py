import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n jungle , 5 , fable \\n vivid , 3 , quiver \\n jungle , 2 , vivid \\n vivid , oops , fable \\n ember , 9 , fable \\n  , 4 , quiver \\n vivid , 7 , quiver \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'ember': {'total': 9, 'count': 1, 'categories': ['fable']}, 'jungle': {'total': 7, 'count': 2, 'categories': ['fable', 'vivid']}, 'vivid': {'total': 10, 'count': 2, 'categories': ['quiver']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
