import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n grove , 5 , ripple \\n ultra , 3 , bravo \\n grove , 2 , saffron \\n ultra , oops , ripple \\n thunder , 9 , ripple \\n  , 4 , bravo \\n ultra , 7 , bravo \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'grove': {'total': 7, 'count': 2, 'categories': ['ripple', 'saffron']}, 'thunder': {'total': 9, 'count': 1, 'categories': ['ripple']}, 'ultra': {'total': 10, 'count': 2, 'categories': ['bravo']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
