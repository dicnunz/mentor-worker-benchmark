import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n lantern , 5 , dynamo \\n hazel , 3 , lotus \\n lantern , 2 , meadow \\n hazel , oops , dynamo \\n quill , 9 , dynamo \\n  , 4 , lotus \\n hazel , 7 , lotus \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'hazel': {'total': 10, 'count': 2, 'categories': ['lotus']}, 'lantern': {'total': 7, 'count': 2, 'categories': ['dynamo', 'meadow']}, 'quill': {'total': 9, 'count': 1, 'categories': ['dynamo']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
