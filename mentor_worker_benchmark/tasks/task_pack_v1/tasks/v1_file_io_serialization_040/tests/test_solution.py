import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n ripple , 5 , quartz \\n sierra , 3 , xylem \\n ripple , 2 , golf \\n sierra , oops , quartz \\n feather , 9 , quartz \\n  , 4 , xylem \\n sierra , 7 , xylem \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'feather': {'total': 9, 'count': 1, 'categories': ['quartz']}, 'ripple': {'total': 7, 'count': 2, 'categories': ['golf', 'quartz']}, 'sierra': {'total': 10, 'count': 2, 'categories': ['xylem']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
