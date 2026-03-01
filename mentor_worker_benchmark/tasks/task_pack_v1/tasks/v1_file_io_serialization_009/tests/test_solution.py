import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n nova , 6 , oasis \\n maple , 3 , knight \\n nova , 2 , grove \\n maple , oops , oasis \\n xenon , 9 , oasis \\n  , 4 , knight \\n maple , 7 , knight \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'maple': {'total': 10, 'count': 2, 'categories': ['knight']}, 'nova': {'total': 8, 'count': 2, 'categories': ['grove', 'oasis']}, 'xenon': {'total': 9, 'count': 1, 'categories': ['oasis']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
