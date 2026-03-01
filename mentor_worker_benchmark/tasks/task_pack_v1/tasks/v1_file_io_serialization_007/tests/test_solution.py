import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n timber , 8 , iris \\n yearling , 3 , quiver \\n timber , 2 , harbor \\n yearling , oops , iris \\n dynamo , 9 , iris \\n  , 4 , quiver \\n yearling , 7 , quiver \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'dynamo': {'total': 9, 'count': 1, 'categories': ['iris']}, 'timber': {'total': 10, 'count': 2, 'categories': ['harbor', 'iris']}, 'yearling': {'total': 10, 'count': 2, 'categories': ['quiver']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
