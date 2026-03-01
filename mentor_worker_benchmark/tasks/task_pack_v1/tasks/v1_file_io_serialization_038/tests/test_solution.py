import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n zenith , 7 , acorn \\n grove , 3 , canyon \\n zenith , 2 , kepler \\n grove , oops , acorn \\n prairie , 9 , acorn \\n  , 4 , canyon \\n grove , 7 , canyon \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'grove': {'total': 10, 'count': 2, 'categories': ['canyon']}, 'prairie': {'total': 9, 'count': 1, 'categories': ['acorn']}, 'zenith': {'total': 9, 'count': 2, 'categories': ['acorn', 'kepler']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
