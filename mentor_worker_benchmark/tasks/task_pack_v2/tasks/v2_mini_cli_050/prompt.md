# Mini-Repo CLI Task (easy)

Implement CLI behavior in `src/cli.py` for a local utility.

Requirements:
- Parse `--values` as comma-separated integers.
- Support modes: `sum`, `max`, `median`.
- Apply `--bias` to final numeric output.
- `--as-json` prints a JSON object with `mode` and `value`.
- Keep CLI entrypoint `main(argv: list[str] | None = None) -> int`.
