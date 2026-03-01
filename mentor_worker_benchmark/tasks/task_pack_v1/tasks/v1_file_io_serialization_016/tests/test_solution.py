import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n vivid , 5 , quest \\n meadow , 3 , zenith \\n vivid , 2 , lotus \\n meadow , oops , quest \\n beacon , 9 , quest \\n  , 4 , zenith \\n meadow , 7 , zenith \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'beacon': {'total': 9, 'count': 1, 'categories': ['quest']}, 'meadow': {'total': 10, 'count': 2, 'categories': ['zenith']}, 'vivid': {'total': 7, 'count': 2, 'categories': ['lotus', 'quest']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
