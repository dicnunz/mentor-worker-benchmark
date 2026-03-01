import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n piper , 5 , drift \\n kernel , 3 , alpha \\n piper , 2 , dynamo \\n kernel , oops , drift \\n utopia , 9 , drift \\n  , 4 , alpha \\n kernel , 7 , alpha \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'kernel': {'total': 10, 'count': 2, 'categories': ['alpha']}, 'piper': {'total': 7, 'count': 2, 'categories': ['drift', 'dynamo']}, 'utopia': {'total': 9, 'count': 1, 'categories': ['drift']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
