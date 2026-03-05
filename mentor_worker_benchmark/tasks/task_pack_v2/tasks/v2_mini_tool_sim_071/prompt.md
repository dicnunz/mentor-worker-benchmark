# Mini-Repo Tool-Use Simulation (hard)

This task simulates a local analyzer workflow completely offline.

A tool output file is provided in `data/analyzer_output.txt`.
Update parsing and aggregation in:
- `src/parser.py`
- `src/pipeline.py`

Requirements:
- Parse tool lines formatted as `RULE:<rule>|SEVERITY:<level>|FILE:<path>|LINE:<n>`.
- Severity ordering: `info < warn < error`.
- `summarize_from_report(path, min_severity)` should filter by min severity and return:
  - `count`
  - `by_severity`
  - `top_rule` (highest frequency, tie -> lexical)

You do not need to execute any tool; use the provided file contents.
