import json

from src.cli import main


def test_cli_sum_mode(capsys) -> None:
    code = main(["--values", '5,1,7', "--mode", "sum", "--bias", 1])
    assert code == 0
    output = capsys.readouterr().out.strip()
    assert output == str(14)


def test_cli_median_mode(capsys) -> None:
    code = main(["--values", '5,1,7', "--mode", "median", "--bias", 1])
    assert code == 0
    output = capsys.readouterr().out.strip()
    assert output == str(6)


def test_cli_json_output(capsys) -> None:
    code = main(
        ["--values", '5,1,7', "--mode", "max", "--bias", 1, "--as-json"]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload == {"mode": "max", "value": 8}
