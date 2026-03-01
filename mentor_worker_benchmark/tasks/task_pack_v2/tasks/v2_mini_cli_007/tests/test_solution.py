import json

from src.cli import main


def test_cli_sum_mode(capsys) -> None:
    code = main(["--values", '6,2,8', "--mode", "sum", "--bias", 2])
    assert code == 0
    output = capsys.readouterr().out.strip()
    assert output == str(18)


def test_cli_median_mode(capsys) -> None:
    code = main(["--values", '6,2,8', "--mode", "median", "--bias", 2])
    assert code == 0
    output = capsys.readouterr().out.strip()
    assert output == str(8)


def test_cli_json_output(capsys) -> None:
    code = main(
        ["--values", '6,2,8', "--mode", "max", "--bias", 2, "--as-json"]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload == {"mode": "max", "value": 10}
