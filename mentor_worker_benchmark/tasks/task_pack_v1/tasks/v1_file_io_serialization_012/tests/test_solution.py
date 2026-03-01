import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n alpha , 5 , quartz \\n eagle , 3 , river \\n alpha , 2 , legend \\n eagle , oops , quartz \\n acorn , 9 , quartz \\n  , 4 , river \\n eagle , 7 , river \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'acorn': {'total': 9, 'count': 1, 'categories': ['quartz']}, 'alpha': {'total': 7, 'count': 2, 'categories': ['legend', 'quartz']}, 'eagle': {'total': 10, 'count': 2, 'categories': ['river']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
