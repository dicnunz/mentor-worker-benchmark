import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n quest , 5 , cinder \\n quill , 3 , dawn \\n quest , 2 , jade \\n quill , oops , cinder \\n jungle , 9 , cinder \\n  , 4 , dawn \\n quill , 7 , dawn \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'jungle': {'total': 9, 'count': 1, 'categories': ['cinder']}, 'quest': {'total': 7, 'count': 2, 'categories': ['cinder', 'jade']}, 'quill': {'total': 10, 'count': 2, 'categories': ['dawn']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
