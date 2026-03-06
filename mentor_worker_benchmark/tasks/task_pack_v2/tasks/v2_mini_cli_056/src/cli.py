import argparse
import json

from .core import evaluate
from .parsing import parse_values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--values", required=True)
    parser.add_argument("--mode", default="sum")
    parser.add_argument("--bias", type=int, default=0)
    parser.add_argument("--as-json", action="store_true")
    args = parser.parse_args(argv)

    values = parse_values(args.values)
    value = evaluate(values, mode=args.mode, bias=args.bias)
    # Buggy: ignores --as-json.
    print(value)
    return 0
