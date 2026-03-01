import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n saffron , 7 , yankee \\n acorn , 3 , nectarine \\n saffron , 2 , galaxy \\n acorn , oops , yankee \\n nebula , 9 , yankee \\n  , 4 , nectarine \\n acorn , 7 , nectarine \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'acorn': {'total': 10, 'count': 2, 'categories': ['nectarine']}, 'nebula': {'total': 9, 'count': 1, 'categories': ['yankee']}, 'saffron': {'total': 9, 'count': 2, 'categories': ['galaxy', 'yankee']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
