import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n jungle , 7 , warden \\n prairie , 3 , maple \\n jungle , 2 , saffron \\n prairie , oops , warden \\n ripple , 9 , warden \\n  , 4 , maple \\n prairie , 7 , maple \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'jungle': {'total': 9, 'count': 2, 'categories': ['saffron', 'warden']}, 'prairie': {'total': 10, 'count': 2, 'categories': ['maple']}, 'ripple': {'total': 9, 'count': 1, 'categories': ['warden']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
