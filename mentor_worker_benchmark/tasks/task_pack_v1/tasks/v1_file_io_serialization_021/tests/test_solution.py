import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n zenith , 6 , piper \\n india , 3 , xpress \\n zenith , 2 , vertex \\n india , oops , piper \\n beacon , 9 , piper \\n  , 4 , xpress \\n india , 7 , xpress \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'beacon': {'total': 9, 'count': 1, 'categories': ['piper']}, 'india': {'total': 10, 'count': 2, 'categories': ['xpress']}, 'zenith': {'total': 8, 'count': 2, 'categories': ['piper', 'vertex']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
