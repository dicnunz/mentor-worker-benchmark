# mentor-worker-benchmark

A fully local, reproducible benchmark for measuring whether a **mentor LLM** improves a **worker LLM** on objective coding tasks.

- Local inference: [Ollama](https://ollama.com/) only (free/local runtime)
- Objective grading: per-task `pytest` pass/fail
- Mentor restriction: mentor can send **guidance text only** (no code/diff output)
- Artifacts:
  - `results/results.json`
  - `results/leaderboard.md`

## What is new in this version

This repo now includes a versioned generated task corpus:

- Task pack: `task_pack_v1`
- Total tasks: **300**
- Splits:
  - `train`: 200
  - `dev`: 50
  - `test`: 50
- Quick suite: 18 balanced eval tasks (3 per category)

### Categories (6)

1. `string_regex_parsing`
2. `ds_algo`
3. `file_io_serialization`
4. `concurrency_basics`
5. `numerical_edge_cases`
6. `multi_file_mini_module`

## Benchmark design

For each worker model/task:

1. **Baseline**: worker-alone patch attempt
2. **Mentored**: turn-based mentor+worker loop (default `max_turns=4`)

Scoring is objective:

- apply worker patch
- run `pytest`
- record pass/fail and metrics

Mentorship lift is computed as:

`mentored_pass_rate - baseline_pass_rate`

## Mentor constraint enforcement

Mentor responses are checked for violations (code fences, diff markers, file/code-like lines).
If violated, output is sanitized into guidance-only text and violation is logged.

## Task pack versioning + generation

Task pack assets live under:

- `mentor_worker_benchmark/tasks/task_pack_v1/metadata.json`
- `mentor_worker_benchmark/tasks/task_pack_v1/tasks/<task_id>/...`

Regenerate deterministically:

```bash
python -m mentor_worker_benchmark.tasks.task_pack_v1.generate_task_pack --seed 1337
```

`metadata.json` records task id, title, category, difficulty, split, quick flag, and path.

## Setup

Python 3.11+ is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m mentor_worker_benchmark setup
```

Default Ollama model set:

- `llama3.1:8b`
- `qwen2.5-coder:7b`
- `mistral:7b`
- `phi3:mini`
- `gemma2:9b`

## Run commands

### Single command after setup (default eval)

By default, `run` executes **dev+test** split from `task_pack_v1`.

```bash
python -m mentor_worker_benchmark run --models default --max-turns 4
```

### Quick/dev/test/all suites

```bash
python -m mentor_worker_benchmark run --suite quick --max-turns 2
python -m mentor_worker_benchmark run --suite dev --max-turns 4
python -m mentor_worker_benchmark run --suite test --max-turns 4
python -m mentor_worker_benchmark run --suite all --max-turns 4
```

### Select task pack / seed

```bash
python -m mentor_worker_benchmark run --task-pack task_pack_v1 --suite dev --seed 1337
```

### Legacy explicit task selector (still supported)

```bash
python -m mentor_worker_benchmark run --tasks quick
python -m mentor_worker_benchmark run --tasks v1_ds_algo_001,v1_numerical_edge_cases_010
```

## Sanity check (no model calls)

Validate harness/task integrity by running starter tests for selected tasks:

```bash
python -m mentor_worker_benchmark sanity --task-pack task_pack_v1 --suite all --seed 1337
```

Expected behavior for this benchmark style: starter code is incomplete/buggy, so tests should fail with normal assertion failures (not harness errors).

## CLI reference

```bash
python -m mentor_worker_benchmark setup [--models default|m1,m2] [--skip-pull]
python -m mentor_worker_benchmark run [--models ...] [--suite quick|dev|test|all] [--task-pack task_pack_v1] [--seed 1337]
python -m mentor_worker_benchmark sanity [--suite quick|dev|test|all] [--task-pack task_pack_v1] [--seed 1337]
python -m mentor_worker_benchmark leaderboard --results results/results.json --output results/leaderboard.md
```

## Output artifacts

- `results/results.json`: full config, run logs, pass/fail metrics, aggregates
- `results/leaderboard.md`: mentor ranking, worker ranking, pair matrix

Example leaderboard snippet:

```md
## Best Workers
| Worker | Baseline | Mentored | Delta |
| --- | --- | --- | --- |
| qwen2.5-coder:7b | 0.58 | 0.66 | 0.08 |
| phi3:mini | 0.42 | 0.51 | 0.09 |
```

## Reproducibility notes

- Benchmark execution is 100% local once models are pulled.
- Task materialization uses temporary directories and cleanup.
- Task ordering is deterministic per `--seed`.
- Task pack generation is deterministic per seed.

## License

MIT
