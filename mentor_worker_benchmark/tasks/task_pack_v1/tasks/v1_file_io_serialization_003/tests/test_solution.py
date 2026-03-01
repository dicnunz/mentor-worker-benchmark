import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n jungle , 8 , ripple \\n vivid , 3 , xenon \\n jungle , 2 , sunset \\n vivid , oops , ripple \\n nectarine , 9 , ripple \\n  , 4 , xenon \\n vivid , 7 , xenon \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'jungle': {'total': 10, 'count': 2, 'categories': ['ripple', 'sunset']}, 'nectarine': {'total': 9, 'count': 1, 'categories': ['ripple']}, 'vivid': {'total': 10, 'count': 2, 'categories': ['xenon']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
