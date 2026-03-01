import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n piper , 6 , nectar \\n galaxy , 3 , hotel \\n piper , 2 , quill \\n galaxy , oops , nectar \\n orion , 9 , nectar \\n  , 4 , hotel \\n galaxy , 7 , hotel \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'galaxy': {'total': 10, 'count': 2, 'categories': ['hotel']}, 'orion': {'total': 9, 'count': 1, 'categories': ['nectar']}, 'piper': {'total': 8, 'count': 2, 'categories': ['nectar', 'quill']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
