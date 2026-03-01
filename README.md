# mentor-worker-benchmark

A reproducible, fully local benchmark for measuring how much a **mentor LLM** helps a **worker LLM** solve objective coding tasks using only natural-language messages.

- Inference server: [Ollama](https://ollama.com/) (local, free runtime)
- Task type: Python microtasks with `pytest` tests
- Evaluation: objective pass/fail only (no subjective judging)
- Outputs:
  - `results/results.json` (full run logs + metrics)
  - `results/leaderboard.md` (human-friendly rankings)

## Why this project

Many “LLM collaboration” claims are anecdotal. This benchmark isolates one question:

> Does mentorship-style guidance improve worker task success, compared to the same worker alone?

It does this with deterministic local settings (`temperature=0`, `top_p=1`) and test-based scoring.

## Core design

### Roles

- **Worker**: produces the actual unified diff patch.
- **Mentor**: can only send natural-language guidance.

### Mentor constraints

Mentor outputs are checked for code/diff leakage. If violations are detected (diff fences, file content patterns, code-like lines), output is sanitized to guidance-only text and logged as a violation.

### Benchmark modes

For each worker model and task:
1. **Baseline**: worker alone
2. **Mentored**: mentor + worker iterative loop (`max_turns=4` by default)

Mentorship lift is computed as:

`mentored_pass_rate - baseline_pass_rate`

### Task suite

12 tasks across 3 objective categories:
- `bugfix` (4)
- `implement` (4)
- `refactor` (4)

Each task folder contains:
- `prompt.md`
- `src/solution.py`
- `tests/test_solution.py`

## Repo structure

```text
mentor_worker_benchmark/
  __init__.py
  __main__.py
  cli.py
  runner.py
  ollama_client.py
  tasks/
    task_base.py
    task_codegen_py/
      task_defs.py
      harness.py
      templates/
      task_cases/
results/
scripts/install_ollama.sh
pyproject.toml
README.md
LICENSE
```

## Models (default)

The benchmark defaults to these Ollama models:

- `llama3.1:8b`
- `qwen2.5-coder:7b`
- `mistral:7b`
- `phi3:mini`
- `gemma2:9b`

## Setup

Python 3.11+ is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m mentor_worker_benchmark setup
```

`setup` will:
- verify Ollama installation
- try to detect/start Ollama server
- pull missing default models

## Single-command benchmark run (after setup)

```bash
python -m mentor_worker_benchmark run --models default --max-turns 4 --tasks all
```

Quick smoke run:

```bash
python -m mentor_worker_benchmark run --models default --max-turns 2 --tasks quick
```

Render leaderboard from existing results:

```bash
python -m mentor_worker_benchmark leaderboard --results results/results.json
```

## CLI reference

```bash
python -m mentor_worker_benchmark setup [--models default|m1,m2] [--skip-pull]
python -m mentor_worker_benchmark run --models default --max-turns 4 --tasks all
python -m mentor_worker_benchmark leaderboard --results results/results.json --output results/leaderboard.md
```

## Metrics recorded

Per run (`mentor`, `worker`, `task`, `mode`):
- `pass` (bool)
- `turns_used`
- `wall_time_seconds`
- `total_tokens_estimate` (chars/4 approximation)

Aggregates:
- best mentors (avg lift across workers + mentored pass rate)
- best workers (baseline vs mentored pass rates)
- mentor-worker pair matrix

## Example leaderboard snippet

```md
## Best Workers
| Worker | Baseline | Mentored | Delta |
| --- | --- | --- | --- |
| qwen2.5-coder:7b | 0.58 | 0.66 | 0.08 |
| phi3:mini | 0.42 | 0.51 | 0.09 |
```

## Notes on reproducibility

- Runs are local-only and offline after model pulls.
- Task execution is isolated in temporary directories.
- Deterministic generation parameters are used by default.

## License

MIT
