import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n amber , 6 , quiver \\n yearling , 3 , willow \\n amber , 2 , eagle \\n yearling , oops , quiver \\n pioneer , 9 , quiver \\n  , 4 , willow \\n yearling , 7 , willow \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'amber': {'total': 8, 'count': 2, 'categories': ['eagle', 'quiver']}, 'pioneer': {'total': 9, 'count': 1, 'categories': ['quiver']}, 'yearling': {'total': 10, 'count': 2, 'categories': ['willow']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
