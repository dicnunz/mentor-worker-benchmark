import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n timber , 8 , mercury \\n velvet , 3 , amber \\n timber , 2 , quill \\n velvet , oops , mercury \\n jasper , 9 , mercury \\n  , 4 , amber \\n velvet , 7 , amber \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'jasper': {'total': 9, 'count': 1, 'categories': ['mercury']}, 'timber': {'total': 10, 'count': 2, 'categories': ['mercury', 'quill']}, 'velvet': {'total': 10, 'count': 2, 'categories': ['amber']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
