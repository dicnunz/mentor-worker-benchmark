import json

from src.cli import main


def test_cli_sum_mode(capsys) -> None:
    code = main(["--values", '4,2,9', "--mode", "sum", "--bias", 0])
    assert code == 0
    output = capsys.readouterr().out.strip()
    assert output == str(15)


def test_cli_median_mode(capsys) -> None:
    code = main(["--values", '4,2,9', "--mode", "median", "--bias", 0])
    assert code == 0
    output = capsys.readouterr().out.strip()
    assert output == str(4)


def test_cli_json_output(capsys) -> None:
    code = main(
        ["--values", '4,2,9', "--mode", "max", "--bias", 0, "--as-json"]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload == {"mode": "max", "value": 9}
