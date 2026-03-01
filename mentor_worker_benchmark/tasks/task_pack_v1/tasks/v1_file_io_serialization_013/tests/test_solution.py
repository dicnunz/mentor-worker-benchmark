import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n utopia , 6 , kepler \\n ember , 3 , nectar \\n utopia , 2 , piper \\n ember , oops , kepler \\n fable , 9 , kepler \\n  , 4 , nectar \\n ember , 7 , nectar \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'ember': {'total': 10, 'count': 2, 'categories': ['nectar']}, 'fable': {'total': 9, 'count': 1, 'categories': ['kepler']}, 'utopia': {'total': 8, 'count': 2, 'categories': ['kepler', 'piper']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
