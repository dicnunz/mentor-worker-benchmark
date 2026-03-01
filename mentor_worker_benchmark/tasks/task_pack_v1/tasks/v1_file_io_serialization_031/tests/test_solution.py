import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n willow , 8 , fable \\n prairie , 3 , foxtrot \\n willow , 2 , ivory \\n prairie , oops , fable \\n yonder , 9 , fable \\n  , 4 , foxtrot \\n prairie , 7 , foxtrot \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'prairie': {'total': 10, 'count': 2, 'categories': ['foxtrot']}, 'willow': {'total': 10, 'count': 2, 'categories': ['fable', 'ivory']}, 'yonder': {'total': 9, 'count': 1, 'categories': ['fable']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
