import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n zenith , 6 , orion \\n opal , 3 , jungle \\n zenith , 2 , thunder \\n opal , oops , orion \\n india , 9 , orion \\n  , 4 , jungle \\n opal , 7 , jungle \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'india': {'total': 9, 'count': 1, 'categories': ['orion']}, 'opal': {'total': 10, 'count': 2, 'categories': ['jungle']}, 'zenith': {'total': 8, 'count': 2, 'categories': ['orion', 'thunder']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
