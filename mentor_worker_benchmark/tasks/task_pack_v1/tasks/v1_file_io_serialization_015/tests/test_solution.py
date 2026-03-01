import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n nectarine , 8 , voyage \\n prairie , 3 , zen \\n nectarine , 2 , sierra \\n prairie , oops , voyage \\n xenon , 9 , voyage \\n  , 4 , zen \\n prairie , 7 , zen \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'nectarine': {'total': 10, 'count': 2, 'categories': ['sierra', 'voyage']}, 'prairie': {'total': 10, 'count': 2, 'categories': ['zen']}, 'xenon': {'total': 9, 'count': 1, 'categories': ['voyage']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
