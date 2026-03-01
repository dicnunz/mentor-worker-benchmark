import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n meadow , 6 , fable \\n juliet , 3 , zen \\n meadow , 2 , piper \\n juliet , oops , fable \\n xenon , 9 , fable \\n  , 4 , zen \\n juliet , 7 , zen \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'juliet': {'total': 10, 'count': 2, 'categories': ['zen']}, 'meadow': {'total': 8, 'count': 2, 'categories': ['fable', 'piper']}, 'xenon': {'total': 9, 'count': 1, 'categories': ['fable']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
