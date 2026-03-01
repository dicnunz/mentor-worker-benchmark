import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n drift , 8 , rocket \\n fable , 3 , kepler \\n drift , 2 , prairie \\n fable , oops , rocket \\n golf , 9 , rocket \\n  , 4 , kepler \\n fable , 7 , kepler \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'drift': {'total': 10, 'count': 2, 'categories': ['prairie', 'rocket']}, 'fable': {'total': 10, 'count': 2, 'categories': ['kepler']}, 'golf': {'total': 9, 'count': 1, 'categories': ['rocket']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
